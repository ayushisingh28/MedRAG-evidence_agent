import json
from pathlib import Path

from app.service import answer


def test_golden_retrieval_set() -> None:
    cases = json.loads(Path("evals/golden_questions.json").read_text())
    for case in cases:
        response = answer(case["question"], 4)
        found = {source.id for source in response.sources}
        assert found.intersection(case["expected_source_ids"])
