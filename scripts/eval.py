import json
import argparse
import numpy as np

try:
    from rouge_score import rouge_scorer
except ImportError:
    print("Please install rouge_score: pip install rouge_score")
    exit(1)

def run_evaluation(predictions_file, references_file):
    with open(predictions_file, "r") as f:
        preds = json.load(f)
    with open(references_file, "r") as f:
        refs = json.load(f)

    if len(preds) != len(refs):
        print(f"Warning: Mismatched lengths. Preds: {len(preds)}, Refs: {len(refs)}")

    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    scores = {"rouge1": [], "rouge2": [], "rougeL": []}
    
    for p, r in zip(preds, refs):
        score = scorer.score(r, p)
        scores["rouge1"].append(score['rouge1'].fmeasure)
        scores["rouge2"].append(score['rouge2'].fmeasure)
        scores["rougeL"].append(score['rougeL'].fmeasure)
        
    print("--- Evaluation Results ---")
    print(f"ROUGE-1: {np.mean(scores['rouge1']):.4f}")
    print(f"ROUGE-2: {np.mean(scores['rouge2']):.4f}")
    print(f"ROUGE-L: {np.mean(scores['rougeL']):.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Fine-Tuned Gemma Model on CUAD dataset")
    parser.add_argument("--preds", required=True, help="JSON file with model predictions (list of strings)")
    parser.add_argument("--refs", required=True, help="JSON file with ground truth references (list of strings)")
    args = parser.parse_args()
    run_evaluation(args.preds, args.refs)
