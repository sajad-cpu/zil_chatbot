"""Sentence-aware text chunker.

Splits raw text into overlapping chunks suitable for embedding.
Token counts are approximated via word count (1 token ≈ 0.75 words for English).
"""

from __future__ import annotations

import re
from typing import List

DEFAULT_CHUNK_TOKENS = 300   # target ~300 tokens per chunk
DEFAULT_OVERLAP_TOKENS = 50  # sliding-window overlap to preserve context

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")


def _tokens_to_words(tokens: int) -> int:
    return max(1, round(tokens / 0.75))


def chunk_text(
    text: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[str]:
    """Split ``text`` into sentence-aware overlapping chunks."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []

    words_per_chunk = _tokens_to_words(chunk_tokens)
    overlap_words = _tokens_to_words(overlap_tokens)

    sentences = _SENTENCE_RE.findall(cleaned) or [cleaned]

    chunks: List[str] = []
    buffer: List[str] = []
    buffer_word_count = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = sentence.split()
        if buffer_word_count + len(words) > words_per_chunk and buffer:
            chunks.append(" ".join(buffer).strip())
            # Start the next buffer with the tail of the current one for overlap.
            tail = " ".join(buffer).split()[-overlap_words:]
            buffer = [" ".join(tail)] if tail else []
            buffer_word_count = len(tail)
        buffer.append(sentence)
        buffer_word_count += len(words)

    if buffer:
        chunks.append(" ".join(buffer).strip())

    return [c for c in chunks if c]
