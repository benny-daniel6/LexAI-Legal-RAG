"""
Downloads CUAD (Contract Understanding Atticus Dataset) from HuggingFace,
converts to Gemma instruction-tuning format, saves as JSONL.

Usage:
    python fine_tuning/prepare_dataset.py --output data/legal_finetune.jsonl
"""
import argparse
import json
import random
from pathlib import Path


LEGAL_CLAUSE_PROMPTS = {
    "Parties":              "Identify all parties to this contract.",
    "Agreement Date":       "What is the effective date of this agreement?",
    "Expiration Date":      "When does this contract expire or terminate?",
    "Renewal Term":         "Describe the renewal or extension terms.",
    "Governing Law":        "Which governing law and jurisdiction applies?",
    "Indemnification":      "Extract the indemnification clause in full.",
    "Limitation of Liability": "What are the limitations of liability stated?",
    "IP Ownership":         "Who owns the intellectual property created under this agreement?",
    "Non-Compete":          "Describe any non-compete or exclusivity restrictions.",
    "Termination for Cause": "Under what conditions may this agreement be terminated for cause?",
    "Confidentiality":      "What are the confidentiality obligations of each party?",
    "Warranty":             "What warranties are provided and by whom?",
}

GEMMA_TEMPLATE = """\
<start_of_turn>user
You are a specialist legal AI. {instruction}

CONTRACT EXCERPT:
{context}
<end_of_turn>
<start_of_turn>model
{answer}
<end_of_turn>"""


def format_example(instruction: str, context: str, answer: str) -> dict:
    return {
        "text": GEMMA_TEMPLATE.format(
            instruction=instruction,
            context=context.strip()[:2000],
            answer=answer.strip(),
        )
    }


def load_cuad(split: str = "train"):
    try:
        from datasets import load_dataset
        return load_dataset("cuad", split=split, trust_remote_code=True)
    except Exception as e:
        print(f"Could not load CUAD dataset: {e}")
        return None


def build_dataset(output_path: str, max_samples: int = 5000):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading CUAD dataset...")
    dataset = load_cuad("train")

    if dataset is None:
        print("Dataset unavailable. Generating synthetic samples instead.")
        _write_synthetic(output_path)
        return

    examples = []
    for row in dataset:
        context = row.get("context", "")
        if not context:
            continue
        for clause_type, prompt in LEGAL_CLAUSE_PROMPTS.items():
            answers = row.get("answers", {}).get("text", [])
            if answers:
                answer = answers[0]
            else:
                answer = f"This clause type ({clause_type}) is not explicitly addressed in the provided excerpt."
            examples.append(format_example(prompt, context, answer))
        if len(examples) >= max_samples:
            break

    random.shuffle(examples)
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Saved {len(examples)} examples to {output_path}")


def _write_synthetic(output_path: Path):
    """Minimal synthetic fallback so training can still run."""
    synthetic = [
        format_example(
            "Identify all parties to this contract.",
            "This Agreement is entered into as of January 1, 2024, between Acme Corp ('Company') "
            "and John Doe ('Consultant').",
            "The parties to this contract are: (1) Acme Corp, referred to as 'Company', and "
            "(2) John Doe, referred to as 'Consultant'.",
        ),
        format_example(
            "Extract the indemnification clause in full.",
            "Each party shall indemnify, defend, and hold harmless the other party from any claims, "
            "damages, losses, and expenses arising out of or relating to such party's breach of "
            "this Agreement.",
            "Indemnification Clause: Each party agrees to indemnify, defend, and hold harmless the "
            "other party and its affiliates from any third-party claims, damages, losses, and "
            "reasonable legal expenses arising from: (a) breach of this Agreement; (b) gross "
            "negligence or willful misconduct.",
        ),
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in synthetic:
            f.write(json.dumps(ex) + "\n")
    print(f"Wrote {len(synthetic)} synthetic samples to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/legal_finetune.jsonl")
    parser.add_argument("--max_samples", type=int, default=5000)
    args = parser.parse_args()
    build_dataset(args.output, args.max_samples)
