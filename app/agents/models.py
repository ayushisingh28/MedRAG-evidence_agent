from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1_500)
    max_sources: int = Field(default=4, ge=1, le=8)


class Source(BaseModel):
    id: str
    title: str
    organization: str
    url: str
    published_on: date
    excerpt: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    safety_notice: str
    status: str
    planned_queries: list[str] = Field(default_factory=list)
    retrieval_backend: str = "memory"
    generation_mode: str = "extractive_fallback"
    verification_status: str = "verified"
    agent_trace: list["AgentTrace"] = Field(default_factory=list)


class AgentTrace(BaseModel):
    agent: str
    outcome: str
    detail: str


class PubMedIngestRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    max_results: int = Field(default=10, ge=1, le=25)


class IngestionJob(BaseModel):
    id: str
    source: Literal["pubmed", "openfda"]
    query: str
    status: Literal["queued", "running", "completed", "failed"]
    documents_added: int = 0
    error: str | None = None


class OpenFdaIngestRequest(BaseModel):
    drug_name: str = Field(min_length=2, max_length=100)
    max_results: int = Field(default=10, ge=1, le=25)
