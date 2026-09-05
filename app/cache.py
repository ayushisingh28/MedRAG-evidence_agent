import hashlib
import time

from app.models import AskResponse


class AnswerCache:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 500) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._values: dict[str, tuple[float, AskResponse]] = {}

    def _key(self, question: str, max_sources: int, corpus_revision: int) -> str:
        value = f"{question.strip().lower()}|{max_sources}|{corpus_revision}"
        return hashlib.sha256(value.encode()).hexdigest()

    def get(self, question: str, max_sources: int, corpus_revision: int) -> AskResponse | None:
        key = self._key(question, max_sources, corpus_revision)
        cached = self._values.get(key)
        if cached is None or cached[0] <= time.monotonic():
            self._values.pop(key, None)
            return None
        return cached[1].model_copy(deep=True)

    def set(
        self, question: str, max_sources: int, corpus_revision: int, response: AskResponse
    ) -> None:
        if len(self._values) >= self.max_entries:
            self._values.pop(next(iter(self._values)))
        self._values[self._key(question, max_sources, corpus_revision)] = (
            time.monotonic() + self.ttl_seconds,
            response.model_copy(deep=True),
        )


answer_cache = AnswerCache()
