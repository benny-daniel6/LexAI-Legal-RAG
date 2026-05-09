# -*- coding: utf-8 -*-
"""
load_test.py
-----------------------------------------------------------------------------
Hammers the LexAI FastAPI backend with concurrent requests to extract
real performance metrics for your resume.

Usage:
    1. Start the server:  uvicorn backend.main:app --host 0.0.0.0 --port 8000
    2. Make sure at least one PDF is uploaded (run test_api.py first)
    3. Run:  python load_test.py

What it measures:
    - P50, P95, P99 latency (milliseconds)
    - Throughput (requests/second)
    - Error rate and HTTP status code distribution
    - Uptime percentage under load
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"

# ── Diverse legal questions to avoid caching bias ─────────────────────────────
LEGAL_QUESTIONS = [
    "What are the indemnification obligations of each party?",
    "What is the termination clause in this agreement?",
    "What are the confidentiality obligations?",
    "What is the governing law for this contract?",
    "What are the intellectual property provisions?",
    "What are the payment terms and conditions?",
    "What are the warranties and representations?",
    "What is the limitation of liability?",
    "What are the non-compete restrictions?",
    "What is the dispute resolution mechanism?",
    "What are the force majeure provisions?",
    "What is the assignment clause?",
    "What are the notice requirements?",
    "What is the severability provision?",
    "What are the data protection obligations?",
    "What is the exclusivity arrangement?",
    "What are the audit rights?",
    "What is the insurance requirement?",
    "What are the reporting obligations?",
    "What is the amendment process for this contract?",
]


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    latency_ms: float
    success: bool
    error: str = ""


@dataclass
class BenchmarkReport:
    endpoint: str
    total_requests: int
    successful: int
    failed: int
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_requests * 100) if self.total_requests else 0

    @property
    def error_rate(self) -> float:
        return 100 - self.success_rate

    @property
    def p50(self) -> float:
        return self._percentile(50)

    @property
    def p95(self) -> float:
        return self._percentile(95)

    @property
    def p99(self) -> float:
        return self._percentile(99)

    @property
    def avg(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def min_lat(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_lat(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0

    def _percentile(self, pct: int) -> float:
        if not self.latencies_ms:
            return 0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * pct / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return sorted_lat[idx]


# ── Request functions ─────────────────────────────────────────────────────────

async def hit_health(client: httpx.AsyncClient) -> RequestResult:
    start = time.perf_counter()
    try:
        r = await client.get(f"{BASE_URL}/health")
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("GET /health", r.status_code, latency, r.status_code == 200)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("GET /health", 0, latency, False, str(e))


async def hit_search(client: httpx.AsyncClient, doc_id: str, question: str) -> RequestResult:
    start = time.perf_counter()
    try:
        r = await client.post(
            f"{BASE_URL}/api/query/search",
            json={"query": question, "doc_id": doc_id, "top_k": 5},
        )
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/query/search", r.status_code, latency, r.status_code == 200)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/query/search", 0, latency, False, str(e))


async def hit_rag_query(client: httpx.AsyncClient, doc_id: str, question: str) -> RequestResult:
    start = time.perf_counter()
    try:
        r = await client.post(
            f"{BASE_URL}/api/query/",
            json={"question": question, "doc_id": doc_id, "top_k": 6, "confidence_threshold": 0.45},
        )
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/query/", r.status_code, latency, r.status_code == 200)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/query/", 0, latency, False, str(e))


async def hit_upload(client: httpx.AsyncClient, pdf_path: str) -> RequestResult:
    start = time.perf_counter()
    try:
        with open(pdf_path, "rb") as f:
            r = await client.post(
                f"{BASE_URL}/api/documents/upload",
                files={"file": ("bench_test.pdf", f, "application/pdf")},
            )
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/documents/upload", r.status_code, latency, r.status_code == 200)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult("POST /api/documents/upload", 0, latency, False, str(e))


# ── Benchmark runners ─────────────────────────────────────────────────────────

async def run_benchmark(
    name: str,
    coro_factory,
    concurrency: int,
    total_requests: int,
) -> BenchmarkReport:
    """Fire `total_requests` using a semaphore to cap concurrency."""
    sem = asyncio.Semaphore(concurrency)
    results: list[RequestResult] = []

    async def _limited(idx: int):
        async with sem:
            return await coro_factory(idx)

    print(f"\n{'-'*60}")
    print(f"  >> {name}")
    print(f"    Concurrency: {concurrency} | Total requests: {total_requests}")
    print(f"{'-'*60}")

    wall_start = time.perf_counter()
    tasks = [asyncio.create_task(_limited(i)) for i in range(total_requests)]

    # Progress tracking
    done_count = 0
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        done_count += 1
        if done_count % 10 == 0 or done_count == total_requests:
            print(f"    Progress: {done_count}/{total_requests}", end="\r")

    wall_elapsed = time.perf_counter() - wall_start
    print()

    report = BenchmarkReport(
        endpoint=name,
        total_requests=total_requests,
        successful=sum(1 for r in results if r.success),
        failed=sum(1 for r in results if not r.success),
        latencies_ms=[r.latency_ms for r in results if r.success],
    )

    # Print errors if any
    errors = [r for r in results if not r.success]
    if errors:
        unique_errors = set(r.error for r in errors if r.error)
        print(f"    [!] {len(errors)} failures. Unique errors:")
        for e in list(unique_errors)[:5]:
            print(f"      -> {e[:120]}")

    throughput = total_requests / wall_elapsed if wall_elapsed > 0 else 0
    print(f"    Wall-clock time: {wall_elapsed:.2f}s | Throughput: {throughput:.1f} req/s")

    return report


def print_report(reports: list[BenchmarkReport]):
    """Print a clean summary table."""
    print("\n")
    print("=" * 90)
    print("  LEXAI LOAD TEST RESULTS")
    print("=" * 90)

    header = f"{'Endpoint':<30} {'Total':>6} {'OK':>5} {'Fail':>5} {'Rate':>7} {'Avg':>8} {'P50':>8} {'P95':>8} {'P99':>8}"
    print(header)
    print("-" * 90)

    for r in reports:
        line = (
            f"{r.endpoint:<30} "
            f"{r.total_requests:>6} "
            f"{r.successful:>5} "
            f"{r.failed:>5} "
            f"{r.success_rate:>6.1f}% "
            f"{r.avg:>7.0f}ms "
            f"{r.p50:>7.0f}ms "
            f"{r.p95:>7.0f}ms "
            f"{r.p99:>7.0f}ms "
        )
        print(line)

    print("-" * 90)

    # Resume bullet point generator
    print("\n")
    print("=" * 90)
    print("  RESUME BULLET POINT (copy-paste ready)")
    print("=" * 90)

    search_report = next((r for r in reports if "search" in r.endpoint.lower()), None)
    rag_report = next((r for r in reports if "query/" in r.endpoint), None)
    health_report = next((r for r in reports if "health" in r.endpoint.lower()), None)

    if search_report:
        print(f"\n  Vector Search (Bi-Encoder only):")
        print(f"  -> Avg latency: {search_report.avg:.0f}ms | P95: {search_report.p95:.0f}ms | "
              f"Uptime: {search_report.success_rate:.1f}% under {search_report.total_requests} concurrent requests")

    if rag_report:
        print(f"\n  Full RAG Pipeline (Retrieve -> Re-rank -> Generate):")
        print(f"  -> Avg latency: {rag_report.avg:.0f}ms | P95: {rag_report.p95:.0f}ms | "
              f"Uptime: {rag_report.success_rate:.1f}% under {rag_report.total_requests} concurrent requests")

    if health_report:
        print(f"\n  Health Check (baseline):")
        print(f"  -> Avg latency: {health_report.avg:.0f}ms | P95: {health_report.p95:.0f}ms")

    print()
    print("  Suggested resume line:")
    if search_report:
        print(f'  "Achieved {search_report.p50:.0f}ms P50 query latency (P95: {search_report.p95:.0f}ms) '
              f'on vector search with {search_report.success_rate:.0f}% uptime '
              f'under {search_report.total_requests} concurrent requests."')
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="LexAI Load Tester")
    parser.add_argument("--concurrency", "-c", type=int, default=50, help="Max concurrent requests (default: 50)")
    parser.add_argument("--requests", "-n", type=int, default=100, help="Total requests per endpoint (default: 100)")
    parser.add_argument("--timeout", "-t", type=int, default=120, help="Per-request timeout in seconds (default: 120)")
    parser.add_argument("--skip-rag", action="store_true", help="Skip full RAG queries (slow if using local LLM)")
    parser.add_argument("--pdf", type=str, default="data/sample_nda.pdf", help="PDF to use for upload benchmark")
    args = parser.parse_args()

    timeout = httpx.Timeout(args.timeout, connect=10.0)
    limits = httpx.Limits(max_connections=args.concurrency + 10, max_keepalive_connections=args.concurrency)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:

        # ── Step 0: Preflight check ───────────────────────────────────────────
        print("=" * 60)
        print("  LEXAI LOAD TESTER")
        print(f"  Target: {BASE_URL}")
        print(f"  Concurrency: {args.concurrency} | Requests/endpoint: {args.requests}")
        print("=" * 60)

        try:
            r = await client.get(f"{BASE_URL}/health")
            assert r.status_code == 200
            print("  [OK] Server is reachable")
        except Exception as e:
            print(f"  [FAIL] Server not reachable at {BASE_URL}: {e}")
            print("     Start it with: uvicorn backend.main:app --host 0.0.0.0 --port 8000")
            return

        # ── Step 1: Get a doc_id to query against ────────────────────────────
        r = await client.get(f"{BASE_URL}/api/documents/")
        docs = r.json()
        if not docs:
            print("  [WARN] No documents indexed. Uploading sample PDF first...")
            with open(args.pdf, "rb") as f:
                r = await client.post(
                    f"{BASE_URL}/api/documents/upload",
                    files={"file": ("sample_nda.pdf", f, "application/pdf")},
                )
            docs = (await client.get(f"{BASE_URL}/api/documents/")).json()

        doc_id = docs[0]["doc_id"]
        total_chunks = sum(d["chunk_count"] for d in docs)
        print(f"  [DOC] Targeting doc_id={doc_id} | Total indexed chunks: {total_chunks}")

        reports: list[BenchmarkReport] = []

        # ── Benchmark 1: Health endpoint (baseline) ──────────────────────────
        report = await run_benchmark(
            name="GET /health",
            coro_factory=lambda i: hit_health(client),
            concurrency=args.concurrency,
            total_requests=args.requests,
        )
        reports.append(report)

        # ── Benchmark 2: Semantic search (bi-encoder only, no LLM) ───────────
        report = await run_benchmark(
            name="POST /api/query/search",
            coro_factory=lambda i: hit_search(client, doc_id, LEGAL_QUESTIONS[i % len(LEGAL_QUESTIONS)]),
            concurrency=args.concurrency,
            total_requests=args.requests,
        )
        reports.append(report)

        # ── Benchmark 3: Full RAG query (retrieve + re-rank + generate) ──────
        if not args.skip_rag:
            report = await run_benchmark(
                name="POST /api/query/ (Full RAG)",
                coro_factory=lambda i: hit_rag_query(client, doc_id, LEGAL_QUESTIONS[i % len(LEGAL_QUESTIONS)]),
                concurrency=args.concurrency,
                total_requests=args.requests,
            )
            reports.append(report)

        # ── Benchmark 4: PDF upload + index pipeline ─────────────────────────
        report = await run_benchmark(
            name="POST /upload (Ingest)",
            coro_factory=lambda i: hit_upload(client, args.pdf),
            concurrency=min(args.concurrency, 10),  # cap to avoid disk thrashing
            total_requests=min(args.requests, 20),   # uploads are heavy, keep it sane
        )
        reports.append(report)

        # ── Final report ─────────────────────────────────────────────────────
        print_report(reports)


if __name__ == "__main__":
    asyncio.run(main())
