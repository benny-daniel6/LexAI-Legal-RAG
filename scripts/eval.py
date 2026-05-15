import json
import argparse
import numpy as np
import httpx
import asyncio
from sentence_transformers import SentenceTransformer, util

LLM_API_URL = "http://localhost:8080/v1"

JUDGE_PROMPT = """\
You are an expert evaluator. Score the provided PREDICTION against the GROUND TRUTH based on the QUESTION.
Output ONLY a JSON object with two keys:
"accuracy": score from 1 to 5 (1=completely wrong, 5=perfect match to ground truth facts)
"relevance": score from 1 to 5 (1=irrelevant/hallucination, 5=directly answers the question)

QUESTION: {question}
GROUND TRUTH: {reference}
PREDICTION: {prediction}
"""

async def evaluate_llm_judge(questions, preds, refs):
    accuracy_scores = []
    relevance_scores = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for q, p, r in zip(questions, preds, refs):
            prompt = JUDGE_PROMPT.format(question=q, prediction=p, reference=r)
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 128,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            try:
                res = await client.post(f"{LLM_API_URL}/chat/completions", json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                score_dict = json.loads(content)
                accuracy_scores.append(int(score_dict.get("accuracy", 1)))
                relevance_scores.append(int(score_dict.get("relevance", 1)))
            except Exception as e:
                print(f"Error calling LLM Judge: {e}")
                accuracy_scores.append(1)
                relevance_scores.append(1)
                
    return np.mean(accuracy_scores), np.mean(relevance_scores)

def run_evaluation(questions_file, predictions_file, references_file):
    with open(questions_file, "r") as f:
        questions = json.load(f)
    with open(predictions_file, "r") as f:
        preds = json.load(f)
    with open(references_file, "r") as f:
        refs = json.load(f)

    if len(preds) != len(refs) or len(preds) != len(questions):
        print("Warning: Mismatched lengths in input files.")

    print("Computing Semantic Textual Similarity (STS)...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    
    sts_scores = []
    for p, r in zip(preds, refs):
        emb_p = model.encode(p, convert_to_tensor=True)
        emb_r = model.encode(r, convert_to_tensor=True)
        sim = util.cos_sim(emb_p, emb_r).item()
        sts_scores.append(sim)
        
    mean_sts = np.mean(sts_scores)
    
    print("Running LLM-as-a-Judge for Accuracy and Relevance...")
    mean_acc, mean_rel = asyncio.run(evaluate_llm_judge(questions, preds, refs))
    
    print("\n--- Semantic Evaluation Results ---")
    print(f"Semantic Textual Similarity (Cosine): {mean_sts:.4f}")
    print(f"LLM Judge Accuracy (1-5): {mean_acc:.2f}")
    print(f"LLM Judge Relevance (1-5): {mean_rel:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Fine-Tuned Model using STS and LLM Judge")
    parser.add_argument("--questions", required=True, help="JSON file with questions")
    parser.add_argument("--preds", required=True, help="JSON file with model predictions")
    parser.add_argument("--refs", required=True, help="JSON file with ground truth references")
    args = parser.parse_args()
    run_evaluation(args.questions, args.preds, args.refs)
