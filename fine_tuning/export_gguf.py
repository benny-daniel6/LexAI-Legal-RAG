"""
Merges LoRA adapters into the base model and exports to GGUF for llama-cpp inference.

Run after train.py:
    python fine_tuning/export_gguf.py --adapter_dir adapters/legal_gemma2 --output_dir models/
"""
import argparse
import os
from pathlib import Path


def merge_and_export(adapter_dir: str, output_dir: str, hf_token: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    BASE_MODEL = "google/gemma-2-2b-it"
    merged_dir = Path(output_dir) / "merged_gemma2_legal"
    merged_dir.mkdir(parents=True, exist_ok=True)

    print("[1/3] Loading base model in float16 for merging")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, token=hf_token)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu",
        token=hf_token,
    )

    print("[2/3] Merging LoRA adapters")
    model = PeftModel.from_pretrained(base_model, adapter_dir)
    model = model.merge_and_unload()
    model.save_pretrained(str(merged_dir))
    tokenizer.save_pretrained(str(merged_dir))
    print(f"  Merged model saved to {merged_dir}")

    print("[3/3] To convert to GGUF, run:")
    print(f"  python llama.cpp/convert_hf_to_gguf.py {merged_dir} --outtype q4_k_m --outfile models/gemma2_legal_Q4_K_M.gguf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter_dir", default="adapters/legal_gemma2")
    parser.add_argument("--output_dir", default="models/")
    parser.add_argument("--hf_token", default=os.getenv("HF_TOKEN", ""))
    args = parser.parse_args()
    merge_and_export(args.adapter_dir, args.output_dir, args.hf_token)
