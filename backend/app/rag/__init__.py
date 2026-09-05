"""
RAG (Retrieval-Augmented Generation) pipeline.

Handles embedding, hybrid retrieval, reranking, and context assembly.
Full implementation in Phase 3.

Submodules (to be created):
- embedder.py          — Sentence-Transformers embedding generation
- vector_store.py      — ChromaDB adapter
- bm25_index.py        — BM25 sparse index
- hybrid_retriever.py  — RRF fusion of vector + BM25 results
- reranker.py          — Cross-encoder reranker
- query_router.py      — Route queries to appropriate retriever
- context_builder.py   — Assemble LLM context with file citations
"""
