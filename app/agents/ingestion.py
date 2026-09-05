import json
import threading
import time
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as element_tree
from datetime import UTC, date, datetime

from app.corpus import repository
from app.models import IngestionJob, Source
from app.storage import store
from app.vector_store import vector_store

PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "MedRAG-Agent/0.1 (public-evidence research tool)"
_jobs_lock = threading.Lock()
_pubmed_request_lock = threading.Lock()
_last_pubmed_request = 0.0


def _request(path: str, parameters: dict[str, str]) -> bytes:
    global _last_pubmed_request
    # NCBI asks clients without an API key to stay at or below three requests per second.
    with _pubmed_request_lock:
        delay = 0.4 - (time.monotonic() - _last_pubmed_request)
        if delay > 0:
            time.sleep(delay)
        _last_pubmed_request = time.monotonic()
    url = f"{PUBMED_BASE_URL}/{path}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def _text(node: element_tree.Element | None, path: str) -> str:
    target = node.find(path) if node is not None else None
    return " ".join(target.itertext()).strip() if target is not None else ""


def _pubmed_sources(query: str, max_results: int) -> list[Source]:
    search = json.loads(
        _request(
            "esearch.fcgi",
            {"db": "pubmed", "term": query, "retmax": str(max_results), "retmode": "json"},
        )
    )
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    payload = _request("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
    root = element_tree.fromstring(payload)
    sources: list[Source] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article, ".//PMID")
        title = _text(article, ".//ArticleTitle")
        abstract = " ".join(
            " ".join(node.itertext()).strip()
            for node in article.findall(".//Abstract/AbstractText")
        )
        year = _text(article, ".//PubDate/Year") or _text(article, ".//ArticleDate/Year")
        if pmid and title and abstract:
            sources.append(
                Source(
                    id=f"pubmed-{pmid}",
                    title=title,
                    organization="PubMed",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    published_on=(
                        date(int(year), 1, 1) if year.isdigit() else datetime.now(UTC).date()
                    ),
                    excerpt=abstract[:2_000],
                    score=0.0,
                )
            )
    return sources


def start_pubmed_job(query: str, max_results: int) -> IngestionJob:
    job = IngestionJob(id=str(uuid.uuid4()), source="pubmed", query=query, status="queued")
    store.save_job(job)
    threading.Thread(target=_run_pubmed_job, args=(job.id, max_results), daemon=True).start()
    return job


def get_job(job_id: str) -> IngestionJob | None:
    return store.get_job(job_id)


def _run_pubmed_job(job_id: str, max_results: int) -> None:
    with _jobs_lock:
        job = store.get_job(job_id)
        if job is None:
            return
        store.save_job(job.model_copy(update={"status": "running"}))
    try:
        added_sources = _pubmed_sources(job.query, max_results)
        added = repository.upsert_many(added_sources)
        vector_store.index(added_sources)
        updated = IngestionJob(
            id=job.id, source="pubmed", query=job.query, status="completed", documents_added=added
        )
    except (OSError, ValueError, json.JSONDecodeError, element_tree.ParseError) as error:
        # Preserve a fetch/parse failure for the API caller without exposing a traceback.
        updated = IngestionJob(
            id=job.id, source="pubmed", query=job.query, status="failed", error=str(error)
        )
    with _jobs_lock:
        store.save_job(updated)


def _openfda_sources(drug_name: str, max_results: int) -> list[Source]:
    url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode(
        {"search": f'openfda.brand_name:"{drug_name}"', "limit": str(max_results)}
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read())
    sources = []
    for result in payload.get("results", []):
        identifier = result.get("id")
        brand_name = ", ".join(result.get("openfda", {}).get("brand_name", [])) or drug_name
        purpose = " ".join(result.get("purpose", []) or result.get("indications_and_usage", []))
        if identifier and purpose:
            sources.append(
                Source(
                    id=f"openfda-{identifier}",
                    title=f"FDA drug label: {brand_name}",
                    organization="U.S. Food and Drug Administration",
                    url="https://open.fda.gov/drug/label/",
                    published_on=datetime.now(UTC).date(),
                    excerpt=purpose[:2_000],
                    score=0.0,
                )
            )
    return sources


def start_openfda_job(drug_name: str, max_results: int) -> IngestionJob:
    job = IngestionJob(id=str(uuid.uuid4()), source="openfda", query=drug_name, status="queued")
    store.save_job(job)
    threading.Thread(target=_run_openfda_job, args=(job.id, max_results), daemon=True).start()
    return job


def _run_openfda_job(job_id: str, max_results: int) -> None:
    with _jobs_lock:
        job = store.get_job(job_id)
        if job is None:
            return
        store.save_job(job.model_copy(update={"status": "running"}))
    try:
        added_sources = _openfda_sources(job.query, max_results)
        added = repository.upsert_many(added_sources)
        vector_store.index(added_sources)
        updated = IngestionJob(
            id=job.id, source="openfda", query=job.query, status="completed", documents_added=added
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        updated = IngestionJob(
            id=job.id, source="openfda", query=job.query, status="failed", error=str(error)
        )
    with _jobs_lock:
        store.save_job(updated)
