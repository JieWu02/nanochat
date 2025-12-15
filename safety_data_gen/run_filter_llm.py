#!/usr/bin/env python3
"""
Entry script for Stage 2: LLM-as-a-Judge filtering.

Usage:
    python -m safety_data_gen.run_filter_llm [--input FILE] [--language en|zh]
"""

import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpt_api import GPTClient
from safety_data_gen.config import (
    STAGE1_ACCEPTED, STAGE2_ACCEPTED, STAGE2_REJECTED,
    LLM_FILTER_STATS, LLM_SAFETY_THRESHOLD, LLM_AVG_OTHER_THRESHOLD,
    ensure_output_dirs
)
from safety_data_gen.filters import filter_llm_judge
from safety_data_gen.utils import save_json, print_stats_table


def main():
    parser = argparse.ArgumentParser(description="Apply LLM-as-a-Judge filtering to conversation data")
    parser.add_argument(
        "--input", "-i",
        default=STAGE1_ACCEPTED,
        help=f"Input file path (default: {STAGE1_ACCEPTED})"
    )
    parser.add_argument(
        "--accepted", "-a",
        default=STAGE2_ACCEPTED,
        help=f"Output file for accepted data (default: {STAGE2_ACCEPTED})"
    )
    parser.add_argument(
        "--rejected", "-r",
        default=STAGE2_REJECTED,
        help=f"Output file for rejected data (default: {STAGE2_REJECTED})"
    )
    parser.add_argument(
        "--language", "-l",
        choices=["en", "zh"],
        default="en",
        help="Language for judge prompts (default: en)"
    )
    parser.add_argument(
        "--safety-threshold", "-s",
        type=int,
        default=LLM_SAFETY_THRESHOLD,
        help=f"Minimum safety score (default: {LLM_SAFETY_THRESHOLD})"
    )
    parser.add_argument(
        "--avg-threshold", "-v",
        type=float,
        default=LLM_AVG_OTHER_THRESHOLD,
        help=f"Minimum average other scores (default: {LLM_AVG_OTHER_THRESHOLD})"
    )
    args = parser.parse_args()

    ensure_output_dirs()

    print("=" * 60)
    print(" Stage 2: LLM-as-a-Judge Filtering")
    print("=" * 60)
    print(f"  Input: {args.input}")
    print(f"  Language: {args.language}")
    print(f"  Safety threshold: {args.safety_threshold}")
    print(f"  Avg other threshold: {args.avg_threshold}")
    print()

    # Check input file exists
    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        print("Run 'python -m safety_data_gen.run_filter_rules' first.")
        sys.exit(1)

    # Clear existing output files
    for f in [args.accepted, args.rejected]:
        if os.path.exists(f):
            os.remove(f)
            print(f"  Cleared existing: {f}")

    # Initialize GPT client
    gpt_client = GPTClient()

    # Run filtering
    stats = filter_llm_judge(
        args.input,
        args.accepted,
        args.rejected,
        gpt_client,
        args.language,
        args.safety_threshold,
        args.avg_threshold
    )

    # Save statistics
    save_json(stats, LLM_FILTER_STATS)
    print(f"\n  Statistics saved to: {LLM_FILTER_STATS}")

    print_stats_table(stats, "LLM Filter Statistics")

    print(f"\nOutput files:")
    print(f"  Accepted: {args.accepted}")
    print(f"  Rejected: {args.rejected}")


if __name__ == "__main__":
    main()
