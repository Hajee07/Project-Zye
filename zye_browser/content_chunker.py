"""
Content Chunking Engine — Day 24.
Splits large web pages and transcripts into semantic chunks without cutting paragraphs or sentences.
"""

from __future__ import annotations

from typing import List


class ContentChunker:
    """Chunks text cleanly within character limits while preserving paragraph and sentence boundaries."""

    @classmethod
    def chunk(cls, text: str, max_chunk_chars: int = 12000) -> List[str]:
        """
        Split text into chunks of at most max_chunk_chars.
        Preserves double newlines (paragraphs) where possible.
        """
        if not text:
            return []

        if len(text) <= max_chunk_chars:
            return [text]

        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)
            if current_len + p_len + 2 <= max_chunk_chars:
                current_chunk.append(p)
                current_len += p_len + 2
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_len = 0

                # If a single paragraph is larger than max_chunk_chars, split on sentence boundary
                if p_len > max_chunk_chars:
                    sentences = p.split(". ")
                    sub_chunk: List[str] = []
                    sub_len = 0
                    for s in sentences:
                        s_len = len(s)
                        if sub_len + s_len + 2 <= max_chunk_chars:
                            sub_chunk.append(s)
                            sub_len += s_len + 2
                        else:
                            if sub_chunk:
                                chunks.append(". ".join(sub_chunk) + ".")
                                sub_chunk = []
                                sub_len = 0
                            # If a single sentence exceeds limit, slice it
                            if s_len > max_chunk_chars:
                                for i in range(0, s_len, max_chunk_chars):
                                    chunks.append(s[i : i + max_chunk_chars])
                            else:
                                sub_chunk.append(s)
                                sub_len = s_len
                    if sub_chunk:
                        chunks.append(". ".join(sub_chunk) + ".")
                else:
                    current_chunk.append(p)
                    current_len = p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks
