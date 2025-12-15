#!/usr/bin/env python3
"""
Evaluate AIME 2024 using HuggingFace model (karpathy/nanochat-d32).

This downloads the model from HuggingFace and uses nanochat's native loading mechanism.

Usage:
    python -m tasks.eval_aime_hf
    python -m tasks.eval_aime_hf --model karpathy/nanochat-d32
"""

import os
import argparse
import pickle
import torch
from huggingface_hub import hf_hub_download

from nanochat.gpt import GPT, GPTConfig
from nanochat.engine import Engine
from tasks.aime import AIME, extract_answer


def load_model_from_hf(repo_id, device="cuda"):
    """Load a nanochat model from HuggingFace Hub."""
    print(f"Downloading model from {repo_id}...")

    # Download files
    model_path = hf_hub_download(repo_id=repo_id, filename="model_000650.pt")
    meta_path = hf_hub_download(repo_id=repo_id, filename="meta_000650.json")
    tokenizer_path = hf_hub_download(repo_id=repo_id, filename="tokenizer.pkl")

    print(f"Model path: {model_path}")
    print(f"Meta path: {meta_path}")
    print(f"Tokenizer path: {tokenizer_path}")

    # Load metadata
    import json
    with open(meta_path, "r") as f:
        meta_data = json.load(f)

    # Load model
    model_data = torch.load(model_path, map_location=device, weights_only=False)

    # Convert bfloat16 to float for CPU
    if device in ("cpu", "mps"):
        model_data = {
            k: v.float() if v.dtype == torch.bfloat16 else v
            for k, v in model_data.items()
        }

    # Fix torch compile prefix
    model_data = {k.removeprefix("_orig_mod."): v for k, v in model_data.items()}

    # Build model
    model_config_kwargs = meta_data["model_config"]
    print(f"Model config: {model_config_kwargs}")
    model_config = GPTConfig(**model_config_kwargs)

    with torch.device("meta"):
        model = GPT(model_config)

    model.to_empty(device=device)
    model.init_weights()
    model.load_state_dict(model_data, strict=True, assign=True)
    model.eval()

    # Convert model to bfloat16 on CUDA for consistency
    if device == "cuda":
        model = model.to(torch.bfloat16)

    # Load tokenizer
    with open(tokenizer_path, "rb") as f:
        enc = pickle.load(f)

    # Wrap with RustBPETokenizer
    from nanochat.tokenizer import RustBPETokenizer
    tokenizer = RustBPETokenizer(enc, "<|bos|>")

    return model, tokenizer, meta_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="karpathy/nanochat-d32", help="HuggingFace model repo")
    parser.add_argument("--max-new-tokens", type=int, default=1024, help="Max new tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature (0 for greedy)")
    parser.add_argument("--top-k", type=int, default=50, help="Top-k sampling")
    args = parser.parse_args()

    print("=" * 60)
    print(f" AIME 2024 Evaluation (using {args.model})")
    print("=" * 60)

    # Device setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Load model and tokenizer
    model, tokenizer, meta_data = load_model_from_hf(args.model, device=device)
    engine = Engine(model, tokenizer)

    print(f"Model loaded successfully!")
    print(f"Vocab size: {tokenizer.get_vocab_size()}")

    # Load AIME dataset
    task = AIME(split="train")
    num_problems = task.num_examples()
    print(f"Number of problems: {num_problems}")

    # Run evaluation
    correct = 0
    results = []

    print(f"\nRunning evaluation...")
    print("-" * 60)

    for i in range(num_problems):
        example = task.get_example(i)
        ground_truth = example['answer']

        # Tokenize prompt
        encoded_prompt = tokenizer.render_for_completion(example)

        # Generate
        with torch.no_grad():
            outputs, _ = engine.generate_batch(
                encoded_prompt,
                num_samples=1,
                max_tokens=args.max_new_tokens,
                temperature=args.temperature,
                top_k=args.top_k,
            )

        # Decode response
        prefix_length = len(encoded_prompt)
        response = tokenizer.decode(outputs[0][prefix_length:])

        # Extract answer
        predicted = extract_answer(response)

        # Compare
        try:
            gt_int = int(ground_truth)
            pred_int = int(predicted) if predicted else -1
            is_correct = gt_int == pred_int
        except (ValueError, TypeError):
            is_correct = False

        if is_correct:
            correct += 1

        results.append((i, predicted, ground_truth, is_correct, response[:200]))

        acc = correct / (i + 1) * 100
        status = "✓" if is_correct else "✗"
        print(f"[{i+1:2d}/{num_problems}] {status} Problem {i}: pred={predicted}, gt={ground_truth} | Acc: {acc:.1f}%")

    print("\n" + "=" * 60)
    print(" Final Results")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Correct: {correct}/{num_problems}")
    print(f"Accuracy: {correct/num_problems*100:.2f}%")

    return correct / num_problems


if __name__ == "__main__":
    main()
