# Architecture

`Browser → FastAPI → safety screen → query planner → vector/lexical retrieval → reranker → optional LLM → citation verifier → answer`

Public-source ingestion is asynchronous: `PubMed/openFDA endpoint → background worker → SQLite source/job store → optional Qdrant index`.

The local deployment uses SQLite, in-process cache/rate limits, and a thread worker. For horizontally scaled production, substitute Postgres, Redis, and a durable queue (Celery/RQ) behind the existing repository/cache/job boundaries. Never submit PHI to this application or its model provider.
