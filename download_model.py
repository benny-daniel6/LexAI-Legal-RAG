"""
Downloads the base Gemma 2 2B GGUF from HuggingFace into models/.
Replace with your fine-tuned GGUF after running fine_tuning/export_gguf.py.
"""
from pathlib import Path
from huggingface_hub import hf_hub_download
import os

REPO_ID   = "bartowski/gemma-2-2b-it-GGUF"
FILENAME  = "gemma-2-2b-it-Q4_K_M.gguf"
DEST_DIR  = Path("./models")

def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEST_DIR / FILENAME

    if dest.exists():
        print(f"Model already present: {dest}  ({dest.stat().st_size / 1e9:.2f} GB)")
        return

    token = os.getenv("HF_TOKEN", "")
    print(f"Downloading {FILENAME} from {REPO_ID} (~1.6 GB)")

    hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=str(DEST_DIR),
        token=token or None,
    )
    print(f"Saved to {dest}")

if __name__ == "__main__":
    main()
