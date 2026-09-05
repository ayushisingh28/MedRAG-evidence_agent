from app.corpus import SEED_SOURCES
from app.verification import citations_are_valid


def test_accepts_citation_bound_sentences() -> None:
    assert citations_are_valid("Vaccination is recommended. [1]", SEED_SOURCES)


def test_rejects_unknown_or_missing_citations() -> None:
    assert not citations_are_valid("Vaccination is recommended.", SEED_SOURCES)
    assert not citations_are_valid("Vaccination is recommended. [99]", SEED_SOURCES)
