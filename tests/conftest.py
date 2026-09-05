import pytest


@pytest.fixture(autouse=True)
def disable_optional_model_provider(monkeypatch):
    """Keep deterministic tests independent of a locally running Ollama service."""
    monkeypatch.delenv("MODEL_ENDPOINT", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
