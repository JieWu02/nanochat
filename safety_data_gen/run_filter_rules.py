#!/usr/bin/env python3
"""
Entry script for Stage 1: Rule-based filtering.

Usage:
    python -m safety_data_gen.run_filter_rules [--input FILE] [--threshold SCORE]
"""

import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety_data_gen.config import (
    RAW_OUTPUT, STAGE1_ACCEPTED, STAGE1_REJECTED,
    RULE_FILTER_STATS, RULE_FILTER_THRESHOLD,
    ensure_output_dirs
)
from safety_data_gen.filters import filter_rule_based
from safety_data_gen.utils import save_json, print_stats_table


def main():
    parser = argparse.ArgumentParser(description="Apply rule-based filtering to conversation data")
    parser.add_argument(
        "--input", "-i",
        default=RAW_OUTPUT,
        help=f"Input file path (default: {RAW_OUTPUT})"
    )
    parser.add_argument(
        "--accepted", "-a",
        default=STAGE1_ACCEPTED,
        help=f"Output file for accepted data (default: {STAGE1_ACCEPTED})"
    )
    parser.add_argument(
        "--rejected", "-r",
        default=STAGE1_REJECTED,
        help=f"Output file for rejected data (default: {STAGE1_REJECTED})"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=int,
        default=RULE_FILTER_THRESHOLD,
        help=f"Minimum score to accept (default: {RULE_FILTER_THRESHOLD})"
    )
    args = parser.parse_args()

    ensure_output_dirs()

    print("=" * 60)
    print(" Stage 1: Rule-based Filtering")
    print("=" * 60)
    print(f"  Input: {args.input}")
    print(f"  Threshold: {args.threshold}")
    print()

    # Check input file exists
    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        print("Run 'python -m safety_data_gen.run_generate' first.")
        sys.exit(1)

    # Clear existing output files
    for f in [args.accepted, args.rejected]:
        if os.path.exists(f):
            os.remove(f)
            print(f"  Cleared existing: {f}")

    # Run filtering
    stats = filter_rule_based(args.input, args.accepted, args.rejected, args.threshold)

    # Save statistics
    save_json(stats, RULE_FILTER_STATS)
    print(f"\n  Statistics saved to: {RULE_FILTER_STATS}")

    print_stats_table(stats, "Rule Filter Statistics")

    print(f"\nOutput files:")
    print(f"  Accepted: {args.accepted}")
    print(f"  Rejected: {args.rejected}")


if __name__ == "__main__":
    main()
