"""
Full pipeline for safety data generation.

This module orchestrates the complete pipeline:
- Stage 0: Generate raw data
- Stage 1: Rule-based filtering
- Stage 2: LLM-as-a-Judge filtering
- Stage 3: Generate samples and statistics
"""

import os
import json
import random
from datetime import datetime
from typing import Dict

from .config import (
    RAW_OUTPUT, STAGE1_ACCEPTED, STAGE1_REJECTED,
    STAGE2_ACCEPTED, STAGE2_REJECTED,
    GENERATION_STATS, RULE_FILTER_STATS, LLM_FILTER_STATS,
    SAMPLES_DIR,
    ensure_output_dirs
)
from .generator import generate_all
from .filters import filter_rule_based, filter_llm_judge
from .utils import load_jsonl, save_json, print_stats_table


def generate_samples(input_file: str, output_dir: str, num_samples: int = 5) -> None:
    """
    Generate sample files from the final filtered data.

    Args:
        input_file: Path to final accepted JSONL file
        output_dir: Directory to save sample files
        num_samples: Number of samples per category
    """
    data = load_jsonl(input_file)

    # Group by category
    refusal_samples = [d for d in data if d.get("metadata", {}).get("category") == "refusal"]
    redirection_samples = [d for d in data if d.get("metadata", {}).get("category") == "redirection"]

    os.makedirs(output_dir, exist_ok=True)

    # Sample refusal examples
    if refusal_samples:
        samples = random.sample(refusal_samples, min(num_samples, len(refusal_samples)))
        sample_file = os.path.join(output_dir, "sample_refusal.json")
        save_json({"samples": samples, "count": len(samples)}, sample_file)
        print(f"  Saved {len(samples)} refusal samples to {sample_file}")

    # Sample redirection examples
    if redirection_samples:
        samples = random.sample(redirection_samples, min(num_samples, len(redirection_samples)))
        sample_file = os.path.join(output_dir, "sample_redirection.json")
        save_json({"samples": samples, "count": len(samples)}, sample_file)
        print(f"  Saved {len(samples)} redirection samples to {sample_file}")


def run_full_pipeline(
    gpt_client,
    language: str = "en",
    skip_generation: bool = False,
    skip_rule_filter: bool = False,
    skip_llm_filter: bool = False
) -> Dict:
    """
    Run the complete data generation and filtering pipeline.

    Args:
        gpt_client: GPT client for API calls
        language: "en" or "zh" for prompt language
        skip_generation: Skip raw data generation (use existing)
        skip_rule_filter: Skip rule-based filtering (use existing)
        skip_llm_filter: Skip LLM-as-a-Judge filtering

    Returns:
        Dictionary with all statistics
    """
    ensure_output_dirs()

    print("=" * 60)
    print(" Safety Data Generation Pipeline")
    print("=" * 60)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Language: {language}")
    print()

    all_stats = {}

    # Stage 0: Generate raw data
    if not skip_generation:
        print("-" * 60)
        print("Stage 0: Generating raw data")
        print("-" * 60)

        # Clear existing raw data
        if os.path.exists(RAW_OUTPUT):
            os.remove(RAW_OUTPUT)

        gen_stats = generate_all(gpt_client, RAW_OUTPUT, language)
        save_json(gen_stats, GENERATION_STATS)
        all_stats["generation"] = gen_stats
        print_stats_table(gen_stats, "Generation Statistics")
    else:
        print("Stage 0: Skipped (using existing raw data)")
        if os.path.exists(GENERATION_STATS):
            all_stats["generation"] = load_jsonl(GENERATION_STATS)

    # Stage 1: Rule-based filtering
    if not skip_rule_filter:
        print("-" * 60)
        print("Stage 1: Rule-based filtering")
        print("-" * 60)

        # Clear existing filtered data
        if os.path.exists(STAGE1_ACCEPTED):
            os.remove(STAGE1_ACCEPTED)
        if os.path.exists(STAGE1_REJECTED):
            os.remove(STAGE1_REJECTED)

        rule_stats = filter_rule_based(RAW_OUTPUT, STAGE1_ACCEPTED, STAGE1_REJECTED)
        save_json(rule_stats, RULE_FILTER_STATS)
        all_stats["rule_filter"] = rule_stats
        print_stats_table(rule_stats, "Rule Filter Statistics")
    else:
        print("Stage 1: Skipped (using existing rule-filtered data)")
        if os.path.exists(RULE_FILTER_STATS):
            all_stats["rule_filter"] = load_jsonl(RULE_FILTER_STATS)

    # Stage 2: LLM-as-a-Judge filtering
    if not skip_llm_filter:
        print("-" * 60)
        print("Stage 2: LLM-as-a-Judge filtering")
        print("-" * 60)

        # Clear existing filtered data
        if os.path.exists(STAGE2_ACCEPTED):
            os.remove(STAGE2_ACCEPTED)
        if os.path.exists(STAGE2_REJECTED):
            os.remove(STAGE2_REJECTED)

        llm_stats = filter_llm_judge(STAGE1_ACCEPTED, STAGE2_ACCEPTED, STAGE2_REJECTED, gpt_client, language)
        save_json(llm_stats, LLM_FILTER_STATS)
        all_stats["llm_filter"] = llm_stats
        print_stats_table(llm_stats, "LLM Filter Statistics")
    else:
        print("Stage 2: Skipped (using existing LLM-filtered data)")
        if os.path.exists(LLM_FILTER_STATS):
            all_stats["llm_filter"] = load_jsonl(LLM_FILTER_STATS)

    # Stage 3: Generate samples
    print("-" * 60)
    print("Stage 3: Generating samples")
    print("-" * 60)

    final_file = STAGE2_ACCEPTED if not skip_llm_filter else STAGE1_ACCEPTED
    generate_samples(final_file, SAMPLES_DIR)

    # Final summary
    print("=" * 60)
    print(" Pipeline Complete")
    print("=" * 60)
    print(f"  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  Output files:")
    print(f"    Raw data: {RAW_OUTPUT}")
    print(f"    Stage 1 accepted: {STAGE1_ACCEPTED}")
    print(f"    Stage 1 rejected: {STAGE1_REJECTED}")
    print(f"    Stage 2 accepted: {STAGE2_ACCEPTED}")
    print(f"    Stage 2 rejected: {STAGE2_REJECTED}")
    print(f"    Samples: {SAMPLES_DIR}")
    print()

    # Final counts
    if "generation" in all_stats:
        print(f"  Generated: {all_stats['generation'].get('success', 'N/A')} conversations")
    if "rule_filter" in all_stats:
        print(f"  After rule filter: {all_stats['rule_filter'].get('accepted', 'N/A')} conversations")
    if "llm_filter" in all_stats:
        print(f"  After LLM filter: {all_stats['llm_filter'].get('accepted', 'N/A')} conversations (final)")

    print("=" * 60)

    return all_stats
