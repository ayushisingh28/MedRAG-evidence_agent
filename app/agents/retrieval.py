import re

from app.corpus import repository
from app.models import Source
from app.reranker import rerank
from app.vector_store import vector_store


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def retrieve_many(queries: list[str], limit: int) -> list[Source]:
    combined_question = " ".join(queries)
    if vector_store.backend == "qdrant":
        vector_store.index(repository.all_sources())
        return rerank(combined_question, vector_store.search(combined_question, limit=50), limit)

    query_terms = set().union(*(_terms(query) for query in queries))
    if not query_terms:
        return []
    ranked: list[Source] = []
    for source in repository.all_sources():
        document_terms = _terms(f"{source.title} {source.organization} {source.excerpt}")
        overlap = len(query_terms & document_terms)
        if overlap:
            ranked.append(source.model_copy(update={"score": round(overlap / len(query_terms), 3)}))
    candidates = sorted(ranked, key=lambda item: item.score, reverse=True)[:50]
    return rerank(combined_question, candidates, limit)


def retrieve(question: str, limit: int) -> list[Source]:
    return retrieve_many([question], limit)
