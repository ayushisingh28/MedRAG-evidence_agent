import os
import uuid
from collections.abc import Iterable

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.embeddings import VECTOR_SIZE, embed
from app.models import Source

COLLECTION = "clinical_evidence"


class VectorStore:
    def __init__(self) -> None:
        self.backend = os.getenv("VECTOR_BACKEND", "memory").lower()
        if self.backend != "qdrant":
            self.client = None
        elif path := os.getenv("QDRANT_PATH"):
            self.client = QdrantClient(path=path)
        else:
            self.client = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

    def index(self, sources: Iterable[Source]) -> None:
        if self.client is None:
            return
        source_list = list(sources)
        if not source_list:
            return
        if not self.client.collection_exists(COLLECTION):
            self.client.create_collection(
                COLLECTION, vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"medrag-source:{source.id}")),
                vector=embed(f"{source.title} {source.excerpt}"),
                payload=source.model_dump(mode="json"),
            )
            for source in source_list
        ]
        self.client.upsert(collection_name=COLLECTION, points=points, wait=True)

    def search(self, question: str, limit: int) -> list[Source]:
        if self.client is None or not self.client.collection_exists(COLLECTION):
            return []
        results = self.client.query_points(
            collection_name=COLLECTION, query=embed(question), limit=limit, with_payload=True
        ).points
        return [
            Source.model_validate({**result.payload, "score": round(result.score, 3)})
            for result in results
            if result.payload
        ]

    def count(self) -> int:
        if self.client is None or not self.client.collection_exists(COLLECTION):
            return 0
        return self.client.count(collection_name=COLLECTION, exact=True).count


vector_store = VectorStore()
