#!/usr/bin/env python3
"""
Entry script for Stage 0: Generate raw safety conversation data.

Usage:
    python -m safety_data_gen.run_generate [--language en|zh]
"""

import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpt_api import GPTClient
from safety_data_gen.config import RAW_OUTPUT, GENERATION_STATS, ensure_output_dirs
from safety_data_gen.generator import generate_all
from safety_data_gen.utils import save_json, print_stats_table


def main():
    parser = argparse.ArgumentParser(description="Generate raw safety conversation data")
    parser.add_argument(
        "--language", "-l",
        choices=["en", "zh"],
        default="en",
        help="Language for prompts (default: en)"
    )
    parser.add_argument(
        "--output", "-o",
        default=RAW_OUTPUT,
        help=f"Output file path (default: {RAW_OUTPUT})"
    )
    args = parser.parse_args()

    ensure_output_dirs()

    print("=" * 60)
    print(" Stage 0: Generate Raw Data")
    print("=" * 60)
    print(f"  Language: {args.language}")
    print(f"  Output: {args.output}")
    print()

    # Clear existing output
    if os.path.exists(args.output):
        os.remove(args.output)
        print(f"  Cleared existing output file")

    # Initialize GPT client
    gpt_client = GPTClient()

    # Generate data
    stats = generate_all(gpt_client, args.output, args.language)

    # Save statistics
    save_json(stats, GENERATION_STATS)
    print(f"\n  Statistics saved to: {GENERATION_STATS}")

    print_stats_table(stats, "Generation Statistics")

    print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
