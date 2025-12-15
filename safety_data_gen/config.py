"""
Configuration parameters for safety data generation.
"""

import os

# =============================================================================
# Generation Parameters
# =============================================================================

NUM_CONVERSATIONS = 1000
NUM_WORKERS = 32
CATEGORY_A_COUNT = 500  # Refusal
CATEGORY_B_COUNT = 500  # Redirection

# =============================================================================
# Quality Thresholds
# =============================================================================

# Rule-based filter threshold (score 0-100)
RULE_FILTER_THRESHOLD = 40  # Reject if score < 40

# LLM judge thresholds
LLM_SAFETY_THRESHOLD = 4     # Reject if safety < 4
LLM_AVG_OTHER_THRESHOLD = 3  # Reject if avg(naturalness, completeness, consistency) < 3

# =============================================================================
# Output Paths
# =============================================================================

# Base directory for this module
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

# Output directory
OUTPUT_DIR = os.path.join(MODULE_DIR, "output")

# Raw generation output
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
RAW_OUTPUT = os.path.join(RAW_DIR, "raw_conversations.jsonl")

# Stage 1: Rule-based filter output
STAGE1_DIR = os.path.join(OUTPUT_DIR, "stage1_rule_filtered")
STAGE1_ACCEPTED = os.path.join(STAGE1_DIR, "accepted.jsonl")
STAGE1_REJECTED = os.path.join(STAGE1_DIR, "rejected.jsonl")

# Stage 2: LLM judge filter output
STAGE2_DIR = os.path.join(OUTPUT_DIR, "stage2_llm_filtered")
STAGE2_ACCEPTED = os.path.join(STAGE2_DIR, "accepted.jsonl")
STAGE2_REJECTED = os.path.join(STAGE2_DIR, "rejected.jsonl")

# Samples directory
SAMPLES_DIR = os.path.join(OUTPUT_DIR, "samples")

# Statistics directory
STATISTICS_DIR = os.path.join(OUTPUT_DIR, "statistics")
GENERATION_STATS = os.path.join(STATISTICS_DIR, "generation_stats.json")
RULE_FILTER_STATS = os.path.join(STATISTICS_DIR, "rule_filter_stats.json")
LLM_FILTER_STATS = os.path.join(STATISTICS_DIR, "llm_filter_stats.json")

# =============================================================================
# Helper Functions
# =============================================================================

def ensure_output_dirs():
    """Create all output directories if they don't exist."""
    dirs = [
        RAW_DIR,
        STAGE1_DIR,
        STAGE2_DIR,
        SAMPLES_DIR,
        STATISTICS_DIR,
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
