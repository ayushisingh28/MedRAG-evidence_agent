from dataclasses import dataclass, field

from app.generation import synthesize_with_llm
from app.models import AgentTrace, Source
from app.planner import plan
from app.retrieval import retrieve_many
from app.safety import safety_status
from app.verification import citations_are_valid, synthesize_verified


@dataclass
class ResearchState:
    question: str
    max_sources: int
    safety: str | None = None
    queries: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    answer: str = ""
    generation_mode: str = "extractive_fallback"
    verification_status: str = "not_applicable"
    trace: list[AgentTrace] = field(default_factory=list)

    def record(self, agent: str, outcome: str, detail: str) -> None:
        self.trace.append(AgentTrace(agent=agent, outcome=outcome, detail=detail))


class SafetyAgent:
    name = "safety"

    def run(self, state: ResearchState) -> None:
        state.safety = safety_status(state.question)
        if state.safety:
            state.record(self.name, "blocked", f"Request classified as {state.safety}.")
        else:
            state.record(self.name, "cleared", "No emergency or personal-treatment pattern found.")


class PlanningAgent:
    name = "planner"

    def run(self, state: ResearchState) -> None:
        state.queries = plan(state.question)
        state.record(
            self.name, "planned", f"Created {len(state.queries)} research query or queries."
        )


class RetrievalAgent:
    name = "retriever"

    def run(self, state: ResearchState) -> None:
        state.sources = retrieve_many(state.queries, state.max_sources)
        outcome = "retrieved" if state.sources else "insufficient_evidence"
        state.record(
            self.name, outcome, f"Selected {len(state.sources)} source(s) after reranking."
        )


class SynthesisAgent:
    name = "synthesizer"

    def run(self, state: ResearchState) -> None:
        generated = synthesize_with_llm(state.question, state.sources)
        if generated:
            state.answer = generated
            state.generation_mode = "llm"
            state.record(self.name, "generated", "Produced a citation-constrained draft.")
        else:
            state.answer = synthesize_verified(state.sources)
            state.generation_mode = "extractive_fallback"
            state.record(self.name, "extractive", "Used the local citation-bound fallback.")


class CitationVerifierAgent:
    name = "citation_verifier"

    def run(self, state: ResearchState) -> None:
        if state.generation_mode == "extractive_fallback":
            state.verification_status = "verified"
            state.record(
                self.name,
                "verified",
                "Extractive answer is copied directly from retrieved sources.",
            )
            return
        if citations_are_valid(state.answer, state.sources):
            state.verification_status = "verified"
            state.record(
                self.name, "verified", "Every sentence has a valid retrieved-source citation."
            )
            return
        state.answer = synthesize_verified(state.sources)
        state.generation_mode = "extractive_fallback"
        state.verification_status = "fallback_verified"
        state.record(
            self.name, "corrected", "Rejected unsupported draft and used extractive evidence."
        )


class ResearchCoordinator:
    """Explicit state-machine coordinator for the specialized research agents."""

    def __init__(self) -> None:
        self.safety = SafetyAgent()
        self.planner = PlanningAgent()
        self.retriever = RetrievalAgent()
        self.synthesizer = SynthesisAgent()
        self.verifier = CitationVerifierAgent()

    def run(self, question: str, max_sources: int) -> ResearchState:
        state = ResearchState(question=question, max_sources=max_sources)
        self.safety.run(state)
        if state.safety:
            return state
        self.planner.run(state)
        self.retriever.run(state)
        if not state.sources:
            return state
        self.synthesizer.run(state)
        self.verifier.run(state)
        return state
