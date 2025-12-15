"""
Data generation logic for safety conversation data.

This module handles the generation of raw conversation data using LLM APIs.
"""

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional

from .config import (
    NUM_CONVERSATIONS, NUM_WORKERS,
    CATEGORY_A_COUNT, CATEGORY_B_COUNT,
    RAW_OUTPUT, ensure_output_dirs
)
from .scenarios import SAFETY_SCENARIOS
from .prompts import (
    REFUSAL_PROMPT_TEMPLATE, REFUSAL_PROMPT_TEMPLATE_ZH,
    REDIRECTION_PROMPT_TEMPLATE, REDIRECTION_PROMPT_TEMPLATE_ZH,
    RESPONSE_FORMAT
)
from .utils import append_jsonl, save_json, print_progress


def calculate_distribution() -> Dict[Tuple[str, str], int]:
    """
    Calculate how many conversations to generate per subcategory.

    Returns:
        dict mapping (category, subcategory) -> count
    """
    distribution = {}

    # Category A: Refusal
    refusal_subcats = list(SAFETY_SCENARIOS["refusal"].keys())
    per_subcat_a = CATEGORY_A_COUNT // len(refusal_subcats)
    remainder_a = CATEGORY_A_COUNT % len(refusal_subcats)

    for i, subcat in enumerate(refusal_subcats):
        distribution[("refusal", subcat)] = per_subcat_a + (1 if i < remainder_a else 0)

    # Category B: Redirection
    redirection_subcats = list(SAFETY_SCENARIOS["redirection"].keys())
    per_subcat_b = CATEGORY_B_COUNT // len(redirection_subcats)
    remainder_b = CATEGORY_B_COUNT % len(redirection_subcats)

    for i, subcat in enumerate(redirection_subcats):
        distribution[("redirection", subcat)] = per_subcat_b + (1 if i < remainder_b else 0)

    return distribution


def generate_single_conversation(
    idx: int,
    category: str,
    subcategory: str,
    gpt_client,
    language: str = "en"
) -> Tuple[Optional[List[Dict]], Dict]:
    """
    Generate a single conversation for the given category/subcategory.
    Uses idx as random seed for reproducibility.

    Args:
        idx: Unique index for this conversation (used as random seed)
        category: "refusal" or "redirection"
        subcategory: Specific subcategory name
        gpt_client: GPT client for API calls
        language: "en" or "zh" for prompt language

    Returns:
        (messages, metadata) where messages is list of dicts or None on failure
    """
    rng = random.Random(idx)
    scenario = SAFETY_SCENARIOS[category][subcategory]

    # Sample 3 starters for diversity in prompt
    num_samples = min(3, len(scenario.starters))
    sample_starters = "\n".join(rng.sample(scenario.starters, num_samples))

    # Sample a context variation if available
    context = rng.choice(scenario.context_variations) if scenario.context_variations else "General situation"

    # Select appropriate template based on category and language
    if category == "refusal":
        template = REFUSAL_PROMPT_TEMPLATE_ZH if language == "zh" else REFUSAL_PROMPT_TEMPLATE
    else:
        template = REDIRECTION_PROMPT_TEMPLATE_ZH if language == "zh" else REDIRECTION_PROMPT_TEMPLATE

    # Build the prompt
    prompt = template.format(
        subcategory=subcategory.replace("_", " ").title(),
        subcategory_desc=scenario.description,
        context=context,
        sample_starters=sample_starters
    )

    metadata = {
        "category": category,
        "subcategory": subcategory,
        "idx": idx,
        "language": language
    }

    try:
        # Call API
        content, usage = gpt_client.call_o3(
            prompt,
            reasoning_effort="low",  # Use low for faster generation
            max_completion_tokens=4096,
            timeout=120,  # 2 minutes timeout
        )

        if content is None:
            return None, metadata

        # Parse JSON response
        conversation_data = json.loads(content)
        messages = conversation_data.get("messages", [])

        return messages, metadata

    except json.JSONDecodeError as e:
        print(f"\n[JSON ERROR] idx={idx}: {e}")
        return None, metadata
    except Exception as e:
        print(f"\n[ERROR] idx={idx}: {e}")
        return None, metadata


def _generate_task(args: Tuple) -> Tuple[Optional[List[Dict]], Dict]:
    """Wrapper for parallel generation."""
    idx, category, subcategory, gpt_client, language = args
    return generate_single_conversation(idx, category, subcategory, gpt_client, language)


def generate_all(
    gpt_client,
    output_file: str = RAW_OUTPUT,
    language: str = "en",
    num_workers: int = NUM_WORKERS
) -> Dict:
    """
    Generate all conversations according to the distribution.

    Args:
        gpt_client: GPT client for API calls
        output_file: Path to output JSONL file
        language: "en" or "zh" for prompt language
        num_workers: Number of parallel workers

    Returns:
        Statistics dictionary with counts
    """
    ensure_output_dirs()

    distribution = calculate_distribution()

    # Build list of generation tasks
    tasks = []
    idx = 0
    for (category, subcategory), count in distribution.items():
        for _ in range(count):
            tasks.append((idx, category, subcategory, gpt_client, language))
            idx += 1

    total = len(tasks)
    print(f"Generating {total} conversations...")
    print(f"  Refusal: {CATEGORY_A_COUNT}, Redirection: {CATEGORY_B_COUNT}")

    stats = {
        "total_attempts": total,
        "success": 0,
        "failed": 0,
        "by_category": {
            "refusal": {"success": 0, "failed": 0},
            "redirection": {"success": 0, "failed": 0}
        },
        "by_subcategory": {}
    }

    completed = 0

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(_generate_task, task): task for task in tasks}

        for future in as_completed(futures):
            task = futures[future]
            idx, category, subcategory = task[0], task[1], task[2]

            try:
                messages, metadata = future.result()
            except Exception as e:
                print(f"\n[THREAD ERROR] idx={idx}: {e}")
                messages, metadata = None, {
                    "category": category,
                    "subcategory": subcategory,
                    "idx": idx,
                    "language": language
                }

            # Track stats
            subcat_key = f"{category}/{subcategory}"
            if subcat_key not in stats["by_subcategory"]:
                stats["by_subcategory"][subcat_key] = {"success": 0, "failed": 0}

            if messages is not None:
                # Write to output file
                item = {
                    "messages": messages,
                    "metadata": metadata
                }
                append_jsonl(item, output_file)

                stats["success"] += 1
                stats["by_category"][category]["success"] += 1
                stats["by_subcategory"][subcat_key]["success"] += 1
            else:
                stats["failed"] += 1
                stats["by_category"][category]["failed"] += 1
                stats["by_subcategory"][subcat_key]["failed"] += 1

            completed += 1
            print_progress(completed, total, prefix="  ")

    print()  # New line after progress
    print(f"  Success: {stats['success']}, Failed: {stats['failed']}")

    return stats
