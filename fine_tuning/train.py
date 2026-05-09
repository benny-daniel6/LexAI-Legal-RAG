"""
QLoRA fine-tuning of google/gemma-2-2b-it on legal contract data.
Requires a GPU (Google Colab T4 is sufficient).

Usage:
    python fine_tuning/train.py --dataset data/legal_finetune.jsonl --output_dir adapters/legal_gemma2 --epochs 3
"""
import argparse
import os
from pathlib import Path


def train(dataset_path: str, output_dir: str, epochs: int, hf_token: str):
    import torch
    from datasets import load_dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer

    BASE_MODEL = "google/gemma-2-2b-it"
    print(f"[1/5] Loading base model: {BASE_MODEL}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, token=hf_token, trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        token=hf_token,
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    print("[2/5] Applying LoRA adapters")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("[3/5] Loading dataset")
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    dataset = dataset.train_test_split(test_size=0.1, seed=42)

    print("[4/5] Configuring trainer")
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        report_to="none",
        push_to_hub=False,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        tokenizer=tokenizer,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=2048,
        packing=False,
    )

    print("[5/5] Training")
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Adapter saved to {output_dir}")
    print("Next: run fine_tuning/export_gguf.py to merge and convert to GGUF")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA fine-tune Gemma 2 2B on legal data")
    parser.add_argument("--dataset", default="data/legal_finetune.jsonl")
    parser.add_argument("--output_dir", default="adapters/legal_gemma2")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--hf_token", default=os.getenv("HF_TOKEN", ""))
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    train(args.dataset, args.output_dir, args.epochs, args.hf_token)
