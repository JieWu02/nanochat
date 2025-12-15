"""
Safety Data Generation Module

This module provides tools for generating and filtering safety-focused
SFT (Supervised Fine-Tuning) conversation data.

Submodules:
    - config: Configuration parameters
    - scenarios: Safety scenario definitions
    - prompts: Prompt templates for generation and evaluation
    - generator: Data generation logic
    - filters: Rule-based and LLM-based filtering
    - pipeline: Full data generation pipeline
    - utils: Utility functions

Usage:
    # Run full pipeline
    python -m safety_data_gen.run_pipeline

    # Or run individual stages
    python -m safety_data_gen.run_generate      # Stage 0: Generate raw data
    python -m safety_data_gen.run_filter_rules  # Stage 1: Rule-based filtering
    python -m safety_data_gen.run_filter_llm    # Stage 2: LLM-as-a-Judge filtering
"""

from .config import *
