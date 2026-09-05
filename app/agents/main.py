import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.corpus import repository
from app.ingestion import get_job, start_openfda_job, start_pubmed_job
from app.metrics import metrics
from app.models import (
    AskRequest,
    AskResponse,
    IngestionJob,
    OpenFdaIngestRequest,
    PubMedIngestRequest,
)
from app.security import rate_limiter, require_api_key
from app.service import answer
from app.ui import index_page
from app.vector_store import vector_store

app = FastAPI(
    title="MedRAG Agent API",
    version="0.1.0",
    description="Public clinical evidence research API. Not medical advice; no PHI.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("UI_ORIGIN", "http://127.0.0.1:5173")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.get("/", include_in_schema=False)
def index() -> Response:
    return index_page()


@app.get("/health")
def health() -> dict[str, str | bool | int]:
    return {
        "status": "ok",
        "retrieval_backend": vector_store.backend,
        "api_key_required": bool(os.getenv("MEDRAG_API_KEYS")),
        "environment": os.getenv("APP_ENV", "development"),
        "source_count": len(repository.all_sources()),
        "vector_count": vector_store.count(),
    }


@app.post("/v1/ask", response_model=AskResponse)
def ask(request: AskRequest, client_id: str = Depends(require_api_key)) -> AskResponse:
    rate_limiter.check(client_id)
    response = answer(request.question, request.max_sources)
    metrics.increment(f"ask_{response.status}")
    return response


@app.post("/v1/ingestion/pubmed", response_model=IngestionJob, status_code=status.HTTP_202_ACCEPTED)
def ingest_pubmed(
    request: PubMedIngestRequest, client_id: str = Depends(require_api_key)
) -> IngestionJob:
    rate_limiter.check(client_id)
    metrics.increment("ingest_pubmed")
    return start_pubmed_job(request.query, request.max_results)


@app.post(
    "/v1/ingestion/openfda", response_model=IngestionJob, status_code=status.HTTP_202_ACCEPTED
)
def ingest_openfda(
    request: OpenFdaIngestRequest, client_id: str = Depends(require_api_key)
) -> IngestionJob:
    rate_limiter.check(client_id)
    metrics.increment("ingest_openfda")
    return start_openfda_job(request.drug_name, request.max_results)


@app.get("/v1/ingestion/jobs/{job_id}", response_model=IngestionJob)
def ingestion_job(job_id: str) -> IngestionJob:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return job


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics(client_id: str = Depends(require_api_key)) -> Response:
    rate_limiter.check(client_id)
    return Response(metrics.prometheus(), media_type="text/plain; version=0.0.4")
