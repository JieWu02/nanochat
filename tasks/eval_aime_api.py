#!/usr/bin/env python3
"""
Evaluate AIME 2024 using external API (o3-mini).

Usage:
    python -m tasks.eval_aime_api
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent.futures import ThreadPoolExecutor, as_completed
from tasks.aime import AIME, extract_answer
from gpt_api import GPTClient


def evaluate_single(args):
    """Evaluate a single problem."""
    idx, problem_text, ground_truth, client = args

    try:
        response, _ = client.call_o3(
            problem_text,
            reasoning_effort="medium",
            max_completion_tokens=4096,
            timeout=180,
        )

        if response is None:
            return idx, None, ground_truth, False

        predicted = extract_answer(response)

        # Compare
        try:
            gt_int = int(ground_truth)
            pred_int = int(predicted) if predicted else -1
            is_correct = gt_int == pred_int
        except (ValueError, TypeError):
            is_correct = False

        return idx, predicted, ground_truth, is_correct

    except Exception as e:
        print(f"\n[ERROR] Problem {idx}: {e}")
        return idx, None, ground_truth, False


def main():
    print("=" * 60)
    print(" AIME 2024 Evaluation (using o3-mini API)")
    print("=" * 60)

    # Load dataset
    task = AIME(split="train")
    num_problems = task.num_examples()
    print(f"Number of problems: {num_problems}")

    # Initialize API client
    client = GPTClient()

    # Prepare tasks
    tasks = []
    for i in range(num_problems):
        example = task.get_example(i)
        problem_text = example['messages'][0]['content']
        ground_truth = example['answer']
        tasks.append((i, problem_text, ground_truth, client))

    # Run evaluation with parallel workers
    num_workers = 8
    results = []
    correct = 0

    print(f"\nRunning evaluation with {num_workers} workers...")

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(evaluate_single, t): t[0] for t in tasks}

        for future in as_completed(futures):
            idx, predicted, ground_truth, is_correct = future.result()
            results.append((idx, predicted, ground_truth, is_correct))

            if is_correct:
                correct += 1

            total_done = len(results)
            acc = correct / total_done * 100
            status = "✓" if is_correct else "✗"
            print(f"\r[{total_done}/{num_problems}] {status} Problem {idx}: pred={predicted}, gt={ground_truth} | Acc: {acc:.1f}%", end="", flush=True)

    print("\n")

    # Final results
    print("=" * 60)
    print(" Final Results")
    print("=" * 60)
    print(f"Correct: {correct}/{num_problems}")
    print(f"Accuracy: {correct/num_problems*100:.2f}%")

    # Show details
    print("\n--- Details ---")
    results.sort(key=lambda x: x[0])
    for idx, predicted, ground_truth, is_correct in results:
        status = "✓" if is_correct else "✗"
        print(f"  Problem {idx:2d}: {status} predicted={predicted}, ground_truth={ground_truth}")

    return correct / num_problems


if __name__ == "__main__":
    main()
