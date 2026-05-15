/**
 * LexAI — app.js
 * Pure JS single-page app talking to FastAPI backend.
 * No frameworks, no build step.
 */

const API = 'http://localhost:8000';

// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  docs:        [],
  selectedDoc: null,    // { doc_id, filename, chunk_count }
  messages:    [],      // { role:'user'|'ai', content, meta? }
  citations:   [],      // raw citation objects from API
  highlights:  [],      // text strings to highlight on current page
  currentPage: 1,
  totalPages:  1,
  topK:        6,
  threshold:   0.45,
  analysing:   false,
};

// ─── API helpers ──────────────────────────────────────────────────────────────
async function apiGet(path) {
  try {
    const r = await fetch(API + path);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function apiPost(path, body) {
  try {
    const r = await fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch (e) { return { error: e.message }; }
}

// ─── Health check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  const badge = document.getElementById('health-badge');
  const base  = await apiGet('/health');

  if (!base) {
    badge.textContent = '🔴 Backend offline';
    badge.className   = 'status-pill pill-error';
    return;
  }

  const llm = await apiGet('/api/query/health');
  if (llm?.llm_ready) {
    badge.textContent = `✅ LLM Ready · ${llm.llm_backend}`;
    badge.className   = 'status-pill pill-ready';
  } else if (llm) {
    badge.textContent = '⚠️ Backend up — LLM not loaded';
    badge.className   = 'status-pill pill-warning';
  } else {
    badge.textContent = '⚠️ Backend starting…';
    badge.className   = 'status-pill pill-warning';
  }
}

// ─── Documents ────────────────────────────────────────────────────────────────
async function loadDocuments() {
  const docs = await apiGet('/api/documents/');
  state.docs = docs || [];
  renderDocList();
}

function renderDocList() {
  const list  = document.getElementById('doc-list');
  const empty = state.docs.length === 0;

  if (empty) {
    list.innerHTML = '<div class="doc-empty">No documents indexed yet.<br>Upload a PDF to get started.</div>';
    return;
  }

  list.innerHTML = state.docs.map(d => `
    <div class="doc-item${state.selectedDoc?.doc_id === d.doc_id ? ' active' : ''}"
         data-id="${d.doc_id}" role="button" tabindex="0">
      <span class="doc-icon">📄</span>
      <div class="doc-info">
        <div class="doc-name" title="${escHtml(d.filename)}">${escHtml(d.filename)}</div>
        <div class="doc-meta">${d.chunk_count.toLocaleString()} chunks</div>
      </div>
      <button class="doc-del" data-id="${d.doc_id}" title="Remove from index" aria-label="Delete">✕</button>
    </div>
  `).join('');

  // Click handlers
  list.querySelectorAll('.doc-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.classList.contains('doc-del')) return;
      const doc = state.docs.find(d => d.doc_id === el.dataset.id);
      if (doc) selectDocument(doc);
    });
    el.addEventListener('keydown', e => { if (e.key === 'Enter') el.click(); });
  });

  list.querySelectorAll('.doc-del').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteDocument(btn.dataset.id);
    });
  });
}

async function selectDocument(doc) {
  state.selectedDoc = doc;
  state.currentPage = 1;

  // Fetch page count
  const info = await apiGet(`/api/documents/${doc.doc_id}/info`);
  state.totalPages = info?.page_count ?? 1;

  renderDocList();
  showExampleQuestions();
  loadPage(1, []);
}

async function deleteDocument(docId) {
  await fetch(`${API}/api/documents/${docId}`, { method: 'DELETE' });
  if (state.selectedDoc?.doc_id === docId) {
    state.selectedDoc = null;
    state.totalPages  = 1;
    state.currentPage = 1;
    showPdfEmpty();
  }
  await loadDocuments();
}

// ─── File upload ──────────────────────────────────────────────────────────────
async function uploadFile(file) {
  if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
    alert('Only PDF files are accepted.');
    return;
  }

  const progress = document.getElementById('upload-progress');
  const fill     = document.getElementById('progress-fill');
  const label    = document.getElementById('progress-label');

  progress.classList.remove('hidden');
  fill.style.width = '5%';
  label.textContent = `Uploading ${file.name}…`;

  const fd = new FormData();
  fd.append('file', file);

  // Animate progress while waiting
  let pct = 5;
  const ticker = setInterval(() => {
    pct = Math.min(pct + 3, 85);
    fill.style.width = pct + '%';
  }, 200);

  try {
    const r = await fetch(`${API}/api/documents/upload`, { method: 'POST', body: fd });
    clearInterval(ticker);

    if (r.ok) {
      const data = await r.json();
      fill.style.width = '100%';
      label.textContent = `✓ Indexed ${data.chunks_indexed} chunks from ${data.page_count} pages`;
      await loadDocuments();

      // Auto-select the newly uploaded doc
      const doc = state.docs.find(d => d.doc_id === data.doc_id);
      if (doc) await selectDocument(doc);

      setTimeout(() => progress.classList.add('hidden'), 2500);
    } else {
      const err = await r.json();
      fill.style.width = '100%';
      fill.style.background = 'var(--red)';
      label.textContent = `Upload failed: ${err.detail ?? r.status}`;
      setTimeout(() => { progress.classList.add('hidden'); fill.style.background = ''; }, 3000);
    }
  } catch(e) {
    clearInterval(ticker);
    label.textContent = `Error: ${e.message}`;
    setTimeout(() => progress.classList.add('hidden'), 3000);
  }
}

// ─── PDF Viewer ───────────────────────────────────────────────────────────────
function showPdfEmpty() {
  document.getElementById('pdf-empty').classList.remove('hidden');
  document.getElementById('pdf-img').classList.add('hidden');
  document.getElementById('prev-page').disabled = true;
  document.getElementById('next-page').disabled = true;
  document.getElementById('page-info').textContent = '—';
}

async function loadPage(pageNum, highlights) {
  if (!state.selectedDoc) { showPdfEmpty(); return; }

  const img     = document.getElementById('pdf-img');
  const loading = document.getElementById('pdf-loading');
  const empty   = document.getElementById('pdf-empty');
  const info    = document.getElementById('page-info');
  const prev    = document.getElementById('prev-page');
  const next    = document.getElementById('next-page');

  state.currentPage = pageNum;
  state.highlights  = highlights;

  empty.classList.add('hidden');
  loading.classList.remove('hidden');
  img.classList.add('hidden');
  info.textContent = `Page ${pageNum} of ${state.totalPages}`;
  prev.disabled = pageNum <= 1;
  next.disabled = pageNum >= state.totalPages;

  // Build URL with highlights
  const hl = (highlights || [])
    .slice(0, 4)                                       // cap to avoid huge URLs
    .map(t => `highlight=${encodeURIComponent(t.slice(0, 120))}`)
    .join('&');

  const url = `${API}/api/documents/${state.selectedDoc.doc_id}/page/${pageNum}${hl ? '?' + hl : ''}`;

  // Load image
  const tmpImg = new Image();
  tmpImg.onload = () => {
    img.src = tmpImg.src;
    loading.classList.add('hidden');
    img.classList.remove('hidden');
  };
  tmpImg.onerror = () => {
    loading.classList.add('hidden');
    empty.classList.remove('hidden');
    empty.querySelector('div:last-child').textContent = `Could not render page ${pageNum}`;
  };
  tmpImg.src = url;
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
function showExampleQuestions() {
  const box = document.getElementById('example-qs');
  box.style.display = state.messages.length === 0 ? '' : 'none';
}

function addMessage(role, content, meta) {
  state.messages.push({ role, content, meta });
  renderMessages();
  showExampleQuestions();
}

function renderMessages() {
  const container = document.getElementById('messages');
  container.innerHTML = state.messages.map(msg => {
    const isUser = msg.role === 'user';
    const avatar = isUser ? '👤' : '⚖️';
    const cls    = isUser ? 'user' : 'ai';
    const metaHtml = msg.meta
      ? `<div class="bubble-meta">— LexAI via <code>${escHtml(msg.meta)}</code></div>`
      : '';
    return `
      <div class="message ${cls}">
        <div class="avatar ${cls}">${avatar}</div>
        <div class="bubble">${renderMarkdown(msg.content)}${metaHtml}</div>
      </div>`;
  }).join('');
  container.scrollTop = container.scrollHeight;
}


function showTyping() {
  const container = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'message ai';
  el.id = 'typing-msg';
  el.innerHTML = `
    <div class="avatar ai">⚖️</div>
    <div class="bubble" style="display: flex; align-items: center; gap: 12px; padding: 12px 16px;">
      <div class="typing-indicator" style="margin: 0; padding: 0;">
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
      </div>
      <span id="typing-text" style="color: #f1f5f9; font-size: 0.9em; font-family: 'JetBrains Mono', monospace;">Initializing agent...</span>
    </div>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  // No fake loop — real-time SSE events from the backend update #typing-text
}

function removeTyping() {
  document.getElementById('typing-msg')?.remove();
}

async function sendQuery() {
  if (state.analysing) return;
  const input    = document.getElementById('question-input');
  const question = input.value.trim();
  if (!question) return;

  if (!state.selectedDoc) {
    alert('Please upload and select a document first.');
    return;
  }

  state.analysing = true;
  document.getElementById('analyse-btn').disabled = true;

  addMessage('user', question);
  input.value = '';
  showTyping();

  try {
    const response = await fetch(API + '/api/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        doc_id:               state.selectedDoc.doc_id,
        top_k:                state.topK,
        confidence_threshold: state.threshold,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          const textEl = document.getElementById('typing-text');
          if (event.type === 'routing' && textEl) {
            textEl.textContent = '\u{1F9E0} ' + event.message;
          } else if (event.type === 'tool' && textEl) {
            const icons = { vector_search: '\u{1F4DA}', web_scraper: '\u{1F310}', calculator: '\u{1F9EE}' };
            textEl.textContent = (icons[event.tool] || '\u{1F527}') + ' ' + event.message;
          } else if (event.type === 'synthesis' && textEl) {
            textEl.textContent = '\u2728 ' + event.message;
          } else if (event.type === 'done') {
            finalResult = event;
          }
        } catch {}
      }
    }

    removeTyping();

    if (finalResult) {
      const answer    = finalResult.answer ?? 'No answer generated.';
      const citations = finalResult.citations ?? [];
      const backend   = finalResult.model_backend ?? 'unknown';
      const warning   = finalResult.warning ?? '';
      const prefix = warning === 'no_results' ? '\u26A0\uFE0F ' : warning === 'low_confidence' ? '\u{1F536} ' : '';
      addMessage('ai', prefix + answer, backend);
      state.citations = citations;
      renderCitations(citations);
      if (citations.length > 0) {
        const top = citations[0];
        const hlTexts = citations.filter(c => c.page_num === top.page_num).map(c => c.text_snippet);
        loadPage(top.page_num, hlTexts);
      }
    } else {
      addMessage('ai', 'No answer generated.', 'unknown');
    }
  } catch (e) {
    removeTyping();
    addMessage('ai', 'Error: ' + e.message, 'error');
  }

  state.analysing = false;
  document.getElementById('analyse-btn').disabled = false;
}

function clearChat() {
  state.messages  = [];
  state.citations = [];
  state.highlights = [];
  document.getElementById('messages').innerHTML   = '';
  document.getElementById('citations').innerHTML  = '';
  document.getElementById('citations-empty').classList.remove('hidden');
  showExampleQuestions();
}

// ─── Citations ────────────────────────────────────────────────────────────────
function renderCitations(citations) {
  const list  = document.getElementById('citations');
  const empty = document.getElementById('citations-empty');

  if (!citations.length) {
    empty.classList.remove('hidden');
    list.innerHTML = '';
    return;
  }

  empty.classList.add('hidden');
  list.innerHTML = citations.map((c, i) => {
    const score = Math.round((c.confidence ?? 0) * 100);
    const tier  = score >= 75 ? 'high' : score >= 55 ? 'medium' : 'low';
    const icon  = tier === 'high' ? '🟢' : tier === 'medium' ? '🟡' : '🔴';
    return `
      <div class="citation-card conf-${tier}">
        <div class="citation-header">
          <span class="citation-badge badge-${tier}">${icon} ${score}% · ${tier.toUpperCase()}</span>
          <span class="citation-page">📄 Page ${c.page_num ?? '?'} · ${escHtml(c.source_file ?? '')}</span>
        </div>
        <div class="conf-bar"><div class="conf-fill ${tier}" style="width:${score}%"></div></div>
        <div class="citation-text">${escHtml(c.text_snippet ?? '')}</div>
        <button class="citation-jump" data-page="${c.page_num}" data-text="${escAttr(c.text_snippet ?? '')}">
          ↗ Jump to page ${c.page_num}
        </button>
      </div>`;
  }).join('');

  list.querySelectorAll('.citation-jump').forEach(btn => {
    btn.addEventListener('click', () => {
      const pg  = parseInt(btn.dataset.page);
      const txt = btn.dataset.text;
      // Collect all citation texts on that page
      const hlTexts = state.citations
        .filter(c => c.page_num === pg)
        .map(c => c.text_snippet);
      loadPage(pg, hlTexts);
    });
  });
}

// ─── Tiny markdown renderer ───────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  return escHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`(.+?)`/g,       '<code>$1</code>')
    .replace(/\n/g,            '<br>');
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ─── Event Bindings ───────────────────────────────────────────────────────────
function bindEvents() {
  // File upload — drop zone
  const dz    = document.getElementById('drop-zone');
  const input = document.getElementById('file-input');

  dz.addEventListener('click',   () => input.click());
  dz.addEventListener('keydown', e => { if (e.key === 'Enter') input.click(); });
  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', ()  => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
  input.addEventListener('change', () => {
    if (input.files[0]) uploadFile(input.files[0]);
    input.value = '';
  });

  // Chat
  document.getElementById('analyse-btn').addEventListener('click', sendQuery);
  document.getElementById('clear-btn').addEventListener('click', clearChat);

  const qInput = document.getElementById('question-input');
  qInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(); }
  });

  // Example questions
  document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      qInput.value = btn.dataset.q;
      qInput.focus();
    });
  });

  // PDF navigation
  document.getElementById('prev-page').addEventListener('click', () => {
    if (state.currentPage > 1) loadPage(state.currentPage - 1, state.highlights);
  });
  document.getElementById('next-page').addEventListener('click', () => {
    if (state.currentPage < state.totalPages) loadPage(state.currentPage + 1, state.highlights);
  });

  // RAG sliders
  const topKSlider = document.getElementById('top-k-slider');
  const topKVal    = document.getElementById('top-k-val');
  topKSlider.addEventListener('input', () => {
    state.topK = parseInt(topKSlider.value);
    topKVal.textContent = topKSlider.value;
  });

  const threshSlider = document.getElementById('threshold-slider');
  const threshVal    = document.getElementById('threshold-val');
  threshSlider.addEventListener('input', () => {
    state.threshold = parseInt(threshSlider.value) / 100;
    threshVal.textContent = threshSlider.value + '%';
  });
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
async function init() {
  bindEvents();
  await checkHealth();
  await loadDocuments();
  showExampleQuestions();

  // Re-check health every 20 s
  setInterval(checkHealth, 20_000);
}

init();
