import os
import sqlite3
from pathlib import Path

from app.models import IngestionJob, Source


class SQLiteStore:
    """Durable single-instance store; production can replace this adapter with Postgres."""

    def __init__(self) -> None:
        self.path = Path(
            os.getenv("INCIDENT_DB_PATH", os.getenv("MEDRAG_DB_PATH", "data/medrag.db"))
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, organization TEXT NOT NULL,
                    url TEXT NOT NULL, published_on TEXT NOT NULL, excerpt TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, query TEXT NOT NULL,
                    status TEXT NOT NULL, documents_added INTEGER NOT NULL, error TEXT
                );
                """
            )

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def seed_sources(self, sources: list[Source]) -> None:
        self.upsert_sources(sources)

    def all_sources(self) -> list[Source]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, title, organization, url, published_on, excerpt FROM sources"
            ).fetchall()
        return [
            Source(
                id=row[0],
                title=row[1],
                organization=row[2],
                url=row[3],
                published_on=row[4],
                excerpt=row[5],
                score=0.0,
            )
            for row in rows
        ]

    def upsert_sources(self, sources: list[Source]) -> int:
        if not sources:
            return 0
        with self._connection() as connection:
            before = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            connection.executemany(
                "INSERT OR IGNORE INTO sources VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (s.id, s.title, s.organization, s.url, s.published_on.isoformat(), s.excerpt)
                    for s in sources
                ],
            )
            after = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        return after - before

    def save_job(self, job: IngestionJob) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO ingestion_jobs VALUES (?, ?, ?, ?, ?, ?)",
                (job.id, job.source, job.query, job.status, job.documents_added, job.error),
            )

    def get_job(self, job_id: str) -> IngestionJob | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, source, query, status, documents_added, error FROM ingestion_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        return (
            IngestionJob.model_validate(
                dict(zip(("id", "source", "query", "status", "documents_added", "error"), row))
            )
            if row
            else None
        )


store = SQLiteStore()
