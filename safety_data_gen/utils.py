"""
Utility functions for safety data generation.
"""

import json
import os
import random
from typing import List, Dict, Any, Optional


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load data from a JSONL file."""
    data = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
    return data


def save_jsonl(data: List[Dict[str, Any]], file_path: str, mode: str = "w") -> None:
    """Save data to a JSONL file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, mode, encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def append_jsonl(item: Dict[str, Any], file_path: str) -> None:
    """Append a single item to a JSONL file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def load_json(file_path: str) -> Dict[str, Any]:
    """Load data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> None:
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def format_conversation(messages: List[Dict[str, str]]) -> str:
    """Format a conversation for display or evaluation."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def sample_starters(starters: List[str], count: int = 3) -> str:
    """Sample and format example starters for prompt."""
    if not starters:
        return "- (no example starters available)"
    sampled = random.sample(starters, min(count, len(starters)))
    return "\n".join(f"- {s}" for s in sampled)


def count_jsonl_lines(file_path: str) -> int:
    """Count the number of lines in a JSONL file."""
    if not os.path.exists(file_path):
        return 0
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def get_distribution(
    refusal_count: int,
    redirection_count: int,
    refusal_subcategories: List[str],
    redirection_subcategories: List[str]
) -> List[Dict[str, str]]:
    """
    Generate a shuffled distribution of category assignments.

    Args:
        refusal_count: Total number of refusal conversations
        redirection_count: Total number of redirection conversations
        refusal_subcategories: List of refusal subcategory names
        redirection_subcategories: List of redirection subcategory names

    Returns:
        List of dicts with 'category' and 'subcategory' keys
    """
    distribution = []

    # Distribute refusal conversations evenly across subcategories
    per_refusal_sub = refusal_count // len(refusal_subcategories)
    remainder = refusal_count % len(refusal_subcategories)

    for i, subcategory in enumerate(refusal_subcategories):
        count = per_refusal_sub + (1 if i < remainder else 0)
        for _ in range(count):
            distribution.append({
                "category": "refusal",
                "subcategory": subcategory
            })

    # Distribute redirection conversations evenly across subcategories
    per_redirect_sub = redirection_count // len(redirection_subcategories)
    remainder = redirection_count % len(redirection_subcategories)

    for i, subcategory in enumerate(redirection_subcategories):
        count = per_redirect_sub + (1 if i < remainder else 0)
        for _ in range(count):
            distribution.append({
                "category": "redirection",
                "subcategory": subcategory
            })

    # Shuffle the distribution
    random.shuffle(distribution)

    return distribution


def print_progress(current: int, total: int, prefix: str = "", suffix: str = "") -> None:
    """Print a simple progress indicator."""
    percent = (current / total) * 100 if total > 0 else 0
    print(f"\r{prefix}[{current}/{total}] {percent:.1f}%{suffix}", end="", flush=True)


def print_stats_table(stats: Dict[str, Any], title: str = "Statistics") -> None:
    """Print statistics in a formatted table."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")

    def _print_dict(d: Dict[str, Any], indent: int = 0):
        prefix = "  " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                _print_dict(value, indent + 1)
            else:
                print(f"{prefix}{key}: {value}")

    _print_dict(stats)
    print(f"{'=' * 60}\n")
