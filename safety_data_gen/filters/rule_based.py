"""
Rule-based quality filtering for safety conversation data (Stage 1).

This module provides rule-based quality checks that run fast and filter out
clearly problematic data before the more expensive LLM-as-a-Judge stage.
"""

import re
from typing import List, Dict, Tuple, Optional

from ..config import RULE_FILTER_THRESHOLD
from ..utils import load_jsonl, append_jsonl, save_json, print_progress


def validate_structure(messages: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    Validates the structure of conversation messages.

    Checks:
    1. Messages must be a list
    2. Must have at least 2 messages
    3. Must have even number of messages
    4. Roles must alternate starting with user
    5. Content must be string
    6. Content must not be empty

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    # Check 1: Must be a list
    if not isinstance(messages, list):
        return False, "Messages must be a list"

    # Check 2: Must have at least 2 messages
    if len(messages) < 2:
        return False, "Must have at least 2 messages"

    # Check 3: Must have even number of messages
    if len(messages) % 2 != 0:
        return False, "Must have even number of messages"

    # Check 4: Alternating roles starting with user
    for i, msg in enumerate(messages):
        expected_role = "user" if i % 2 == 0 else "assistant"
        if msg.get("role") != expected_role:
            return False, f"Message {i} should be {expected_role}, got {msg.get('role')}"

        # Check 5: Content must be string
        if not isinstance(msg.get("content"), str):
            return False, f"Message {i} content must be string"

        # Check 6: Content must not be empty
        if not msg.get("content", "").strip():
            return False, f"Message {i} has empty content"

    return True, None


def check_content_quality(messages: List[Dict], category: str, subcategory: str) -> Tuple[int, List[str]]:
    """
    Checks content quality based on category-specific criteria.

    Args:
        messages: List of message dicts
        category: "refusal" or "redirection"
        subcategory: Specific subcategory name

    Returns:
        (quality_score 0-100, list of issues)
    """
    issues = []
    score = 100

    assistant_messages = [m["content"] for m in messages if m["role"] == "assistant"]

    # Check 1: For refusal category, ensure no harmful info leaked
    if category == "refusal":
        HARMFUL_LEAK_PATTERNS = [
            r"here'?s? how",
            r"here is how",
            r"step 1:",
            r"step one:",
            r"step \d+",
            r"first,? you need to",
            r"first,? you'll need",
            r"ingredients:",
            r"materials needed:",
            r"you'll need:",
            r"the recipe is",
            r"to make this,?",
            r"the process is",
            r"mix together",
            r"combine the",
            r"you can make",
            r"you could make",
            r"sure,? here",
            r"okay,? here",
        ]
        for pattern in HARMFUL_LEAK_PATTERNS:
            for resp in assistant_messages:
                if re.search(pattern, resp.lower()):
                    issues.append(f"Potential harmful info leak: matched '{pattern}'")
                    score -= 50

    # Check 2: For refusal category, ensure clear refusal language
    if category == "refusal":
        REFUSAL_INDICATORS = [
            r"i can't",
            r"i cannot",
            r"i'm not able",
            r"i won't",
            r"i'm unable",
            r"not something i can help with",
            r"against my guidelines",
            r"not appropriate",
            r"i'm not going to",
            r"i don't provide",
            r"i can not",
        ]
        has_refusal = any(
            re.search(p, resp.lower())
            for p in REFUSAL_INDICATORS
            for resp in assistant_messages
        )
        if not has_refusal:
            issues.append("Missing clear refusal language")
            score -= 30

    # Check 3: For self-harm content, ensure crisis resources included
    if subcategory == "self_harm":
        RESOURCE_INDICATORS = ["988", "crisis", "hotline", "lifeline", "help line", "helpline", "741741"]
        has_resources = any(
            ind in resp.lower()
            for ind in RESOURCE_INDICATORS
            for resp in assistant_messages
        )
        if not has_resources:
            issues.append("Missing crisis resources for self-harm content")
            score -= 40

    # Check 4: Response length check (too short = low quality)
    avg_assistant_length = sum(len(r) for r in assistant_messages) / len(assistant_messages) if assistant_messages else 0
    if avg_assistant_length < 50:
        issues.append(f"Assistant responses too short (avg {avg_assistant_length:.0f} chars)")
        score -= 20

    # Check 5: No emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    for msg in messages:
        if emoji_pattern.search(msg["content"]):
            issues.append("Contains emojis")
            score -= 10
            break

    return max(0, score), issues


def filter_rule_based(
    input_file: str,
    accepted_file: str,
    rejected_file: str,
    threshold: int = RULE_FILTER_THRESHOLD
) -> Dict:
    """
    Apply rule-based filtering to raw conversation data.

    Args:
        input_file: Path to input JSONL file (raw data)
        accepted_file: Path to output JSONL file for accepted data
        rejected_file: Path to output JSONL file for rejected data
        threshold: Minimum score to accept (default from config)

    Returns:
        Statistics dictionary with counts and rejection reasons
    """
    data = load_jsonl(input_file)
    total = len(data)

    stats = {
        "input_count": total,
        "accepted": 0,
        "rejected": 0,
        "rejection_reasons": {},
        "by_category": {
            "refusal": {"accepted": 0, "rejected": 0},
            "redirection": {"accepted": 0, "rejected": 0}
        },
        "score_distribution": {}
    }

    print(f"Stage 1: Rule-based filtering on {total} conversations...")

    for i, item in enumerate(data):
        messages = item.get("messages", [])
        category = item.get("metadata", {}).get("category", "unknown")
        subcategory = item.get("metadata", {}).get("subcategory", "unknown")

        # Validate structure first
        is_valid, error = validate_structure(messages)
        if not is_valid:
            # Structure invalid - reject
            item["rule_filter"] = {
                "passed": False,
                "score": 0,
                "issues": [error]
            }
            append_jsonl(item, rejected_file)
            stats["rejected"] += 1
            stats["by_category"].setdefault(category, {"accepted": 0, "rejected": 0})["rejected"] += 1
            stats["rejection_reasons"][error] = stats["rejection_reasons"].get(error, 0) + 1
        else:
            # Check content quality
            score, issues = check_content_quality(messages, category, subcategory)

            # Track score distribution
            score_bucket = f"{(score // 10) * 10}-{(score // 10) * 10 + 9}"
            stats["score_distribution"][score_bucket] = stats["score_distribution"].get(score_bucket, 0) + 1

            item["rule_filter"] = {
                "passed": score >= threshold,
                "score": score,
                "issues": issues
            }

            if score >= threshold:
                append_jsonl(item, accepted_file)
                stats["accepted"] += 1
                stats["by_category"].setdefault(category, {"accepted": 0, "rejected": 0})["accepted"] += 1
            else:
                append_jsonl(item, rejected_file)
                stats["rejected"] += 1
                stats["by_category"].setdefault(category, {"accepted": 0, "rejected": 0})["rejected"] += 1
                # Track rejection reasons
                for issue in issues:
                    # Simplify the issue text for grouping
                    simple_issue = issue.split(":")[0] if ":" in issue else issue
                    stats["rejection_reasons"][simple_issue] = stats["rejection_reasons"].get(simple_issue, 0) + 1

        print_progress(i + 1, total, prefix="  ")

    print()  # New line after progress
    print(f"  Accepted: {stats['accepted']}, Rejected: {stats['rejected']}")

    return stats
