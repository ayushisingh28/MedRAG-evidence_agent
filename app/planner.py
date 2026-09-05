import re


def plan(question: str) -> list[str]:
    """Conservative query decomposition, deliberately inspectable until an LLM planner is added."""
    normalized = re.sub(r"\s+", " ", question).strip()
    compare_match = re.search(
        r"compare\s+(.+?)\s+(?:vs\.?|versus|and)\s+(.+?)(?:\s+for\s+(.+))?$",
        normalized,
        re.IGNORECASE,
    )
    if compare_match:
        left, right, context = (part.strip() if part else "" for part in compare_match.groups())
        suffix = f" for {context}" if context else ""
        return [f"{left}{suffix}", f"{right}{suffix}"]

    parts = [
        part.strip(" ?.") for part in re.split(r"\?\s+|\s+and\s+", normalized, flags=re.IGNORECASE)
    ]
    useful_parts = [part for part in parts if len(part.split()) >= 3]
    return useful_parts[:3] or [normalized]
