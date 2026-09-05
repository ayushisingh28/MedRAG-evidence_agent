from app.agents.workflow import ResearchCoordinator
from app.cache import answer_cache
from app.corpus import repository
from app.models import AskResponse
from app.vector_store import vector_store

NOTICE = "For public-literature research only; not medical advice. Do not enter personal health information."
coordinator = ResearchCoordinator()


def answer(question: str, max_sources: int) -> AskResponse:
    state = coordinator.run(question, max_sources)
    if state.safety == "emergency":
        return AskResponse(
            answer=(
                "This may need urgent, in-person assessment. Contact your local emergency number or "
                "go to the nearest emergency department now. This research tool cannot assess an emergency."
            ),
            sources=[],
            safety_notice=NOTICE,
            status="escalated",
            planned_queries=[],
            retrieval_backend=vector_store.backend,
            generation_mode="safety_escalation",
            verification_status="not_applicable",
            agent_trace=state.trace,
        )
    if state.safety == "clinical_review":
        return AskResponse(
            answer=(
                "I can summarize general public evidence, but I can’t diagnose, select treatment, or "
                "give a personal dosage. Please discuss this with a qualified clinician or pharmacist."
            ),
            sources=[],
            safety_notice=NOTICE,
            status="needs_clinician",
            planned_queries=[],
            retrieval_backend=vector_store.backend,
            generation_mode="safety_escalation",
            verification_status="not_applicable",
            agent_trace=state.trace,
        )

    cached = answer_cache.get(question, max_sources, repository.revision())
    if cached:
        return cached
    if not state.sources:
        return AskResponse(
            answer=(
                "I don’t have enough retrieved evidence in the current public-source index to answer "
                "that reliably. Try a narrower literature question or consult a qualified clinician."
            ),
            sources=[],
            safety_notice=NOTICE,
            status="insufficient_evidence",
            planned_queries=state.queries,
            retrieval_backend=vector_store.backend,
            generation_mode="no_answer",
            verification_status="not_applicable",
            agent_trace=state.trace,
        )
    response = AskResponse(
        answer=state.answer,
        sources=state.sources,
        safety_notice=NOTICE,
        status="evidence_summary",
        planned_queries=state.queries,
        retrieval_backend=vector_store.backend,
        generation_mode=state.generation_mode,
        verification_status=state.verification_status,
        agent_trace=state.trace,
    )
    answer_cache.set(question, max_sources, repository.revision(), response)
    return response
