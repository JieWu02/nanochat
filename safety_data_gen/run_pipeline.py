#!/usr/bin/env python3
"""
Entry script for running the full safety data generation pipeline.

Usage:
    python -m safety_data_gen.run_pipeline [--language en|zh] [--skip-*]
"""

import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpt_api import GPTClient
from safety_data_gen.pipeline import run_full_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run the full safety data generation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full pipeline in English
    python -m safety_data_gen.run_pipeline

    # Run full pipeline in Chinese
    python -m safety_data_gen.run_pipeline --language zh

    # Skip generation, only run filtering on existing data
    python -m safety_data_gen.run_pipeline --skip-generation

    # Skip LLM filter (faster, lower quality)
    python -m safety_data_gen.run_pipeline --skip-llm-filter
"""
    )
    parser.add_argument(
        "--language", "-l",
        choices=["en", "zh"],
        default="en",
        help="Language for prompts (default: en)"
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip raw data generation (use existing)"
    )
    parser.add_argument(
        "--skip-rule-filter",
        action="store_true",
        help="Skip rule-based filtering (use existing)"
    )
    parser.add_argument(
        "--skip-llm-filter",
        action="store_true",
        help="Skip LLM-as-a-Judge filtering"
    )
    args = parser.parse_args()

    # Initialize GPT client
    gpt_client = GPTClient()

    # Run pipeline
    stats = run_full_pipeline(
        gpt_client,
        language=args.language,
        skip_generation=args.skip_generation,
        skip_rule_filter=args.skip_rule_filter,
        skip_llm_filter=args.skip_llm_filter
    )


if __name__ == "__main__":
    main()
