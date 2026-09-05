import re

from app.models import Source


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def rerank(question: str, candidates: list[Source], limit: int) -> list[Source]:
    """Second-stage lexical reranker; swappable with a cross-encoder."""
    query_terms = _terms(question)
    ranked: list[Source] = []
    for source in candidates:
        evidence_terms = _terms(f"{source.title} {source.excerpt}")
        lexical_score = len(query_terms & evidence_terms) / max(1, len(query_terms))
        score = (0.65 * source.score) + (0.35 * lexical_score)
        ranked.append(source.model_copy(update={"score": round(score, 3)}))
    return sorted(ranked, key=lambda source: source.score, reverse=True)[:limit]
