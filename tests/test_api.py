from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["api_key_required"] is False


def test_browser_ui_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Evidence, organized for decisions" in response.text


def test_retrieved_answer_has_citation_bound_source() -> None:
    response = client.post("/v1/ask", json={"question": "What is the flu vaccine recommendation?"})
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "evidence_summary"
    assert body["sources"]
    assert "[1]" in body["answer"]
    assert body["planned_queries"]
    assert body["generation_mode"] == "extractive_fallback"
    assert body["verification_status"] == "verified"
    assert [step["agent"] for step in body["agent_trace"]] == [
        "safety",
        "planner",
        "retriever",
        "synthesizer",
        "citation_verifier",
    ]


def test_emergency_question_escalates_without_retrieval() -> None:
    body = client.post("/v1/ask", json={"question": "I have chest pain. What should I do?"}).json()
    assert body["status"] == "escalated"
    assert body["sources"] == []


def test_pubmed_ingestion_job_is_accepted() -> None:
    response = client.post(
        "/v1/ingestion/pubmed", json={"query": "influenza vaccine", "max_results": 1}
    )
    body = response.json()
    assert response.status_code == 202
    assert body["status"] in {"queued", "running", "completed", "failed"}


def test_api_key_is_enforced_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("MEDRAG_API_KEYS", "test-key")
    monkeypatch.setenv("AUTH_MODE", "api_key")
    assert client.post("/v1/ask", json={"question": "What is influenza?"}).status_code == 401
    response = client.post(
        "/v1/ask", json={"question": "What is influenza?"}, headers={"x-api-key": "test-key"}
    )
    assert response.status_code == 200
