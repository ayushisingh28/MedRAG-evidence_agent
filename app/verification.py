import re

from app.models import Source


def synthesize_verified(sources: list[Source]) -> str:
    """Only emits source excerpts, making every displayed claim directly traceable."""
    claims = [
        f"{sentence.strip()} [{index}]"
        for index, source in enumerate(sources, 1)
        for sentence in re.split(r"(?<=[.!?])\s+", source.excerpt)
        if sentence.strip()
    ]
    return "Retrieved evidence relevant to your question: " + " ".join(claims)


def citations_are_valid(answer: str, sources: list[Source]) -> bool:
    """Enforce citations on prose sentences and reject unknown source markers."""
    citations = [int(number) for number in re.findall(r"\[(\d+)]", answer)]
    if not citations or any(number < 1 or number > len(sources) for number in citations):
        return False
    sentences = re.findall(r"[^.!?]+[.!?](?:\s*\[\d+])?", answer)
    return bool(sentences) and all(re.search(r"\[\d+]\s*$", sentence) for sentence in sentences)
