from app.corpus import repository
from app.models import Source


def test_sources_are_persisted_and_deduplicated() -> None:
    source = Source(
        id="test-persistent-source",
        title="Test",
        organization="Test",
        url="https://example.test",
        published_on="2025-01-01",
        excerpt="Persistence test source.",
        score=0,
    )
    repository.upsert_many([source])
    assert any(item.id == source.id for item in repository.all_sources())
    assert repository.upsert_many([source]) == 0
