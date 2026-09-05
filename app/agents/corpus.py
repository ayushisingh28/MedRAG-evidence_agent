from datetime import date

from app.models import Source
from app.storage import store

# Development-only seed data. Production ingestion will retain provenance and fetch dates.
SEED_SOURCES = [
    Source(
        id="cdc-flu-vaccine-2024",
        title="Key Facts About Seasonal Flu Vaccine",
        organization="Centers for Disease Control and Prevention",
        url="https://www.cdc.gov/flu/vaccines/keyfacts.html",
        published_on=date(2024, 8, 16),
        excerpt=(
            "CDC recommends everyone 6 months and older get an annual flu vaccine, with rare "
            "exceptions. Vaccination is especially important for people at higher risk of serious "
            "flu complications."
        ),
        score=0.0,
    ),
    Source(
        id="cdc-antibiotics-2024",
        title="Antibiotic Use and Antimicrobial Resistance",
        organization="Centers for Disease Control and Prevention",
        url="https://www.cdc.gov/antibiotic-use/about/index.html",
        published_on=date(2024, 4, 22),
        excerpt=(
            "Antibiotics treat certain bacterial infections but do not treat viruses such as colds "
            "or flu. Using antibiotics when they are not needed can cause side effects and "
            "contributes to antimicrobial resistance."
        ),
        score=0.0,
    ),
    Source(
        id="who-diabetes-2024",
        title="Diabetes",
        organization="World Health Organization",
        url="https://www.who.int/news-room/fact-sheets/detail/diabetes",
        published_on=date(2024, 11, 14),
        excerpt=(
            "Diabetes is a chronic metabolic disease characterized by elevated blood glucose. "
            "Healthy diet, regular physical activity, maintaining a normal body weight and avoiding "
            "tobacco use are ways to prevent or delay type 2 diabetes."
        ),
        score=0.0,
    ),
]


class SourceRepository:
    """Source facade with a durable SQLite development implementation."""

    def __init__(self, sources: list[Source]) -> None:
        store.seed_sources(sources)
        self._revision = 1

    def all_sources(self) -> list[Source]:
        return store.all_sources()

    def upsert_many(self, sources: list[Source]) -> int:
        added = store.upsert_sources(sources)
        if added:
            self._revision += 1
        return added

    def revision(self) -> int:
        return self._revision


repository = SourceRepository(SEED_SOURCES)
