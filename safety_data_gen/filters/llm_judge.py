"""
LLM-as-a-Judge quality filtering for safety conversation data (Stage 2).

This module uses an LLM to evaluate conversation quality on multiple dimensions:
- Safety: Did the assistant correctly refuse harmful requests?
- Naturalness: Is the conversation natural and fluent?
- Completeness: Are responses complete and helpful?
- Consistency: Is the assistant's attitude consistent?
"""

import json
import re
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import LLM_SAFETY_THRESHOLD, LLM_AVG_OTHER_THRESHOLD, NUM_WORKERS
from ..prompts import LLM_JUDGE_PROMPT_TEMPLATE, LLM_JUDGE_PROMPT_TEMPLATE_ZH
from ..utils import load_jsonl, append_jsonl, format_conversation, print_progress


def llm_judge_quality(
    messages: List[Dict],
    category: str,
    subcategory: str,
    gpt_client,
    language: str = "en"
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Use LLM to judge conversation quality.

    Args:
        messages: The conversation messages
        category: "refusal" or "redirection"
        subcategory: Specific subcategory
        gpt_client: GPT client for API calls
        language: "en" or "zh" for prompt language

    Returns:
        (is_pass, reason, scores_dict)
        - is_pass: True if quality is acceptable
        - reason: Brief explanation
        - scores_dict: Dict with safety, naturalness, completeness, consistency scores (or None on error)
    """
    # Format conversation for the prompt
    conversation_text = format_conversation(messages)

    # Select prompt template based on language
    template = LLM_JUDGE_PROMPT_TEMPLATE_ZH if language == "zh" else LLM_JUDGE_PROMPT_TEMPLATE

    prompt = template.format(
        category=category,
        subcategory=subcategory,
        conversation=conversation_text
    )

    try:
        content, usage = gpt_client.call_o3(
            prompt,
            reasoning_effort="low",  # Use low effort to save cost
            max_completion_tokens=1024,
        )

        if content is None:
            # On API failure, default to pass (don't reject good data due to API issues)
            return True, "LLM judge API failed, defaulting to pass", None

        # Parse JSON response - try to extract JSON from the response
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
            else:
                return True, "Failed to parse LLM judge response, defaulting to pass", None

        is_pass = result.get("pass", True)
        reason = result.get("reason", "No reason provided")
        scores = {
            "safety": result.get("safety", 5),
            "naturalness": result.get("naturalness", 5),
            "completeness": result.get("completeness", 5),
            "consistency": result.get("consistency", 5),
        }

        return is_pass, reason, scores

    except Exception as e:
        # On any error, default to pass
        return True, f"LLM judge error: {str(e)}, defaulting to pass", None


def _evaluate_single(
    item: Dict,
    gpt_client,
    language: str,
    safety_threshold: int,
    avg_other_threshold: float
) -> Tuple[Dict, bool, str, Optional[Dict]]:
    """
    Evaluate a single conversation item.

    Returns:
        (item, is_pass, reason, scores)
    """
    messages = item.get("messages", [])
    metadata = item.get("metadata", {})
    category = metadata.get("category", "unknown")
    subcategory = metadata.get("subcategory", "unknown")

    is_pass, reason, scores = llm_judge_quality(
        messages, category, subcategory, gpt_client, language
    )

    # Override pass decision based on thresholds if scores available
    if scores is not None:
        safety = scores.get("safety", 5)
        naturalness = scores.get("naturalness", 5)
        completeness = scores.get("completeness", 5)
        consistency = scores.get("consistency", 5)

        avg_other = (naturalness + completeness + consistency) / 3

        if safety < safety_threshold:
            is_pass = False
            reason = f"Safety score too low ({safety} < {safety_threshold})"
        elif avg_other < avg_other_threshold:
            is_pass = False
            reason = f"Average other scores too low ({avg_other:.2f} < {avg_other_threshold})"

    return item, is_pass, reason, scores


def filter_llm_judge(
    input_file: str,
    accepted_file: str,
    rejected_file: str,
    gpt_client,
    language: str = "en",
    safety_threshold: int = LLM_SAFETY_THRESHOLD,
    avg_other_threshold: float = LLM_AVG_OTHER_THRESHOLD,
    num_workers: int = NUM_WORKERS
) -> Dict:
    """
    Apply LLM-as-a-Judge filtering to conversation data.

    Args:
        input_file: Path to input JSONL file (rule-filtered data)
        accepted_file: Path to output JSONL file for accepted data
        rejected_file: Path to output JSONL file for rejected data
        gpt_client: GPT client for API calls
        language: "en" or "zh" for prompt language
        safety_threshold: Minimum safety score to accept
        avg_other_threshold: Minimum average of other scores to accept
        num_workers: Number of parallel workers

    Returns:
        Statistics dictionary with counts, reasons, and score averages
    """
    data = load_jsonl(input_file)
    total = len(data)

    stats = {
        "input_count": total,
        "accepted": 0,
        "rejected": 0,
        "api_errors": 0,
        "rejection_reasons": {},
        "by_category": {
            "refusal": {"accepted": 0, "rejected": 0},
            "redirection": {"accepted": 0, "rejected": 0}
        },
        "score_totals": {
            "safety": 0,
            "naturalness": 0,
            "completeness": 0,
            "consistency": 0,
            "count": 0
        }
    }

    print(f"Stage 2: LLM-as-a-Judge filtering on {total} conversations...")

    completed = 0

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _evaluate_single,
                item,
                gpt_client,
                language,
                safety_threshold,
                avg_other_threshold
            ): item
            for item in data
        }

        for future in as_completed(futures):
            try:
                item, is_pass, reason, scores = future.result()
            except Exception as e:
                # Handle unexpected errors
                item = futures[future]
                is_pass = True
                reason = f"Unexpected error: {str(e)}"
                scores = None
                stats["api_errors"] += 1

            category = item.get("metadata", {}).get("category", "unknown")

            # Add LLM judge results to item
            item["llm_judge"] = {
                "passed": is_pass,
                "reason": reason,
                "scores": scores
            }

            # Update score totals if scores available
            if scores is not None:
                for key in ["safety", "naturalness", "completeness", "consistency"]:
                    stats["score_totals"][key] += scores.get(key, 0)
                stats["score_totals"]["count"] += 1

            # Write to appropriate file
            if is_pass:
                append_jsonl(item, accepted_file)
                stats["accepted"] += 1
                stats["by_category"].setdefault(category, {"accepted": 0, "rejected": 0})["accepted"] += 1
            else:
                append_jsonl(item, rejected_file)
                stats["rejected"] += 1
                stats["by_category"].setdefault(category, {"accepted": 0, "rejected": 0})["rejected"] += 1
                # Track rejection reasons (simplified)
                simple_reason = reason.split("(")[0].strip() if "(" in reason else reason
                stats["rejection_reasons"][simple_reason] = stats["rejection_reasons"].get(simple_reason, 0) + 1

            completed += 1
            print_progress(completed, total, prefix="  ")

    print()  # New line after progress

    # Calculate average scores
    if stats["score_totals"]["count"] > 0:
        count = stats["score_totals"]["count"]
        stats["average_scores"] = {
            "safety": round(stats["score_totals"]["safety"] / count, 2),
            "naturalness": round(stats["score_totals"]["naturalness"] / count, 2),
            "completeness": round(stats["score_totals"]["completeness"] / count, 2),
            "consistency": round(stats["score_totals"]["consistency"] / count, 2)
        }
    else:
        stats["average_scores"] = {
            "safety": 0, "naturalness": 0, "completeness": 0, "consistency": 0
        }

    # Remove temporary score totals
    del stats["score_totals"]

    print(f"  Accepted: {stats['accepted']}, Rejected: {stats['rejected']}")
    if stats["api_errors"] > 0:
        print(f"  API Errors: {stats['api_errors']}")

    return stats
