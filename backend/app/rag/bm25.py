"""
Sparse BM25 Keyword Search Engine with code-aware tokenization.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.core.logging import get_logger
from app.rag.chunker import DocumentChunk

logger = get_logger(__name__)


def tokenize_code_and_text(text: str) -> list[str]:
    """
    Code-aware tokenizer that splits identifiers, camelCase, snake_case, and words.
    """
    if not text:
        return []

    tokens: list[str] = []
    # Extract alphanumeric words and identifiers
    raw_words = re.findall(r"[a-zA-Z0-9_]+", text)

    for word in raw_words:
        tokens.append(word.lower())

        # Split snake_case
        if "_" in word:
            parts = [p.lower() for p in word.split("_") if p]
            tokens.extend(parts)

        # Split camelCase / PascalCase
        camel_parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", word)
        if len(camel_parts) > 1:
            tokens.extend([p.lower() for p in camel_parts if p])

    return tokens


class BM25Index:
    """In-memory BM25 index supporting code keyword retrieval and metadata filtering."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._repo_indexes: dict[str, dict[str, Any]] = {}

    def index_chunks(self, repository_id: str, chunks: list[DocumentChunk]) -> None:
        """
        Build BM25 term frequency index for repository chunks.
        """
        if not chunks:
            return

        corpus_tokens = [tokenize_code_and_text(c.content) for c in chunks]
        doc_lengths = [len(toks) for toks in corpus_tokens]
        avg_doc_len = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

        # Term document frequency (DF)
        df: dict[str, int] = Counter()
        doc_freqs: list[Counter] = []

        for toks in corpus_tokens:
            tf = Counter(toks)
            doc_freqs.append(tf)
            for term in tf:
                df[term] += 1

        total_docs = len(chunks)
        idf: dict[str, float] = {}
        for term, freq in df.items():
            # Standard Lucene BM25 IDF formula
            idf[term] = math.log(1.0 + (total_docs - freq + 0.5) / (freq + 0.5))

        self._repo_indexes[repository_id] = {
            "chunks": chunks,
            "doc_freqs": doc_freqs,
            "doc_lengths": doc_lengths,
            "avg_doc_len": avg_doc_len,
            "idf": idf,
            "total_docs": total_docs,
        }
        logger.info("BM25 index built", repo_id=repository_id, total_chunks=len(chunks))

    def query_bm25(
        self,
        repository_id: str,
        query_text: str,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Search chunks using BM25 scoring with metadata filtering.
        """
        filters = filters or {}
        index_data = self._repo_indexes.get(repository_id)
        if not index_data:
            return []

        chunks: list[DocumentChunk] = index_data["chunks"]
        doc_freqs: list[Counter] = index_data["doc_freqs"]
        doc_lengths: list[int] = index_data["doc_lengths"]
        avg_doc_len: float = index_data["avg_doc_len"]
        idf: dict[str, float] = index_data["idf"]

        query_tokens = tokenize_code_and_text(query_text)
        if not query_tokens:
            return []

        scored_chunks: list[tuple[DocumentChunk, float]] = []

        for idx, (chunk, tf_map, doc_len) in enumerate(zip(chunks, doc_freqs, doc_lengths)):
            # Apply metadata filters
            if "file_path" in filters and chunk.file_path != filters["file_path"]:
                continue
            if "language" in filters and chunk.language != filters["language"]:
                continue
            if "source_type" in filters and chunk.source_type != filters["source_type"]:
                continue
            if "symbol_name" in filters and chunk.symbol_name != filters["symbol_name"]:
                continue

            score = 0.0
            for token in query_tokens:
                if token not in tf_map:
                    continue
                tf = tf_map[token]
                term_idf = idf.get(token, 0.0)

                # BM25 term weighting formula
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avg_doc_len))
                score += term_idf * (numerator / denominator)

            if score > 0.0:
                scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
