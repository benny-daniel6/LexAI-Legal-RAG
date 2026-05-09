import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        # Navigate to the local server
        print("Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000")
        
        # Wait for the UI to settle
        time.sleep(2)
        
        # Take an initial screenshot
        page.screenshot(path=str(DOCS_DIR / "demo1.png"))
        print("Captured docs/demo1.png")
        
        # Interact with the UI to show a chat state
        try:
            # Let's try to upload a sample document if it hasn't been uploaded yet
            # First see if we can find the file input
            file_input = page.locator("#file-input")
            if file_input.is_visible(timeout=1000) or True: # It's hidden
                print("Uploading sample_nda.pdf...")
                page.set_input_files("#file-input", "data/sample_nda.pdf")
                # Wait for upload to complete (progress bar hides)
                page.wait_for_selector("#upload-progress", state="hidden", timeout=60000)
                time.sleep(1)
                
                # Now select the document in the sidebar
                page.click(".doc-item")
                time.sleep(1)
                
                # Ask a question
                question = "What are the indemnification obligations of each party?"
                page.fill("#question-input", question)
                page.click("#analyse-btn")
                
                # Wait for the AI to answer (typing indicator disappears)
                page.wait_for_selector(".typing-indicator", state="hidden", timeout=30000)
                time.sleep(2) # Give it a moment to render citations
                
                # Take another screenshot with chat state
                page.screenshot(path=str(DOCS_DIR / "demo2.png"))
                print("Captured docs/demo2.png")
        except Exception as e:
            print(f"Error during interaction: {e}")
            
        browser.close()

if __name__ == "__main__":
    main()
