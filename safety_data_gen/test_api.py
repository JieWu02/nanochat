#!/usr/bin/env python3
"""
Simple test to diagnose API call behavior.
"""

import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpt_api import GPTClient

def test_single_call():
    """Test a single API call."""
    print("Testing single API call...")
    client = GPTClient()

    start = time.time()
    content, usage = client.call_o3(
        "Say hello in one word.",
        reasoning_effort="low",
        max_completion_tokens=100,
        timeout=60,
    )
    elapsed = time.time() - start

    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Content: {content[:100] if content else 'None'}...")
    return elapsed


def test_parallel_calls(num_calls=5, num_workers=5):
    """Test parallel API calls."""
    print(f"\nTesting {num_calls} parallel calls with {num_workers} workers...")
    client = GPTClient()

    def make_call(idx):
        start = time.time()
        content, usage = client.call_o3(
            f"Say the number {idx} in one word.",
            reasoning_effort="low",
            max_completion_tokens=100,
            timeout=60,
        )
        elapsed = time.time() - start
        return idx, elapsed, content is not None

    start_total = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(make_call, i): i for i in range(num_calls)}

        for future in as_completed(futures):
            idx, elapsed, success = future.result()
            results.append((idx, elapsed, success))
            print(f"  Call {idx}: {elapsed:.1f}s, success={success}")

    total_elapsed = time.time() - start_total

    print(f"\n  Total elapsed: {total_elapsed:.1f}s")
    print(f"  Avg per call: {sum(r[1] for r in results) / len(results):.1f}s")
    print(f"  Success rate: {sum(r[2] for r in results)}/{len(results)}")

    # Check if truly parallel
    if total_elapsed < sum(r[1] for r in results) * 0.8:
        print("  ✅ Calls ran in parallel")
    else:
        print("  ❌ Calls may have been serialized!")


if __name__ == "__main__":
    test_single_call()
    test_parallel_calls(num_calls=5, num_workers=5)
