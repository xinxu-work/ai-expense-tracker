"""Small, dependency-free knowledge retriever for the interview Q&A corpus.

This is intentionally a first learning slice rather than the final production
vector-search implementation. It preserves question boundaries and source
line ranges so responses can include useful citations. The class can later be
replaced by a dense embedding/vector-store adapter without changing the API
contract or Foundry tool.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import math
import os
from pathlib import Path
import re
from typing import Any, Optional


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+#/&.-]{1,}")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do",
    "for", "from", "how", "i", "if", "in", "is", "it", "of", "on",
    "or", "should", "the", "to", "what", "when", "where", "which",
    "who", "why", "with", "would", "you",
}


def _tokens(text: str) -> list[str]:
    """Return normalized terms used by the local sparse retriever."""
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if token.lower() not in STOP_WORDS
    ]


def default_knowledge_path() -> Path:
    """Resolve the interview knowledge file without hard-coding it."""
    configured = os.getenv("KNOWLEDGE_BASE_PATH")
    if configured:
        return Path(configured).expanduser()

    # Current workspace layout:
    # Xin_Xin_File/Projects/ai-expense-tracker/api -> Xin_Xin_File/DS/...
    workspace_path = (
        Path(__file__).resolve().parents[3]
        / "DS"
        / "Interview_Prep"
        / "AI_Engineer_Knowledge_QA.md"
    )
    if workspace_path.exists():
        return workspace_path

    # Fallback for a future copy of the knowledge file inside this repository.
    return Path(__file__).resolve().parents[1] / "knowledge" / "AI_Engineer_Knowledge_QA.md"


@dataclass(frozen=True)
class KnowledgeChunk:
    """One question-and-answer unit from the Markdown knowledge base."""

    chunk_id: str
    title: str
    section: str
    content: str
    source_path: str
    line_start: int
    line_end: int

    @property
    def search_text(self) -> str:
        return f"{self.title}\n{self.section}\n{self.content}"

    def citation(self) -> str:
        source_name = Path(self.source_path).name
        return (
            f"{source_name} | {self.chunk_id} | "
            f"lines {self.line_start}-{self.line_end}"
        )


@dataclass(frozen=True)
class KnowledgeMatch:
    chunk: KnowledgeChunk
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "title": self.chunk.title,
            "section": self.chunk.section,
            "content": self.chunk.content,
            "score": round(self.score, 4),
            "citation": self.chunk.citation(),
            "source_path": self.chunk.source_path,
            "line_start": self.chunk.line_start,
            "line_end": self.chunk.line_end,
        }


def parse_markdown_questions(text: str, source_path: str) -> list[KnowledgeChunk]:
    """Parse level-three headings into citation-preserving knowledge chunks."""
    lines = text.splitlines()
    chunks: list[KnowledgeChunk] = []
    section = ""
    current_title: Optional[str] = None
    current_start: Optional[int] = None
    current_body: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal current_title, current_start, current_body
        if current_title is None or current_start is None:
            return

        content = "\n".join(current_body).strip()
        if not content:
            current_title = None
            current_start = None
            current_body = []
            return

        match = re.match(r"(AI-\d+)", current_title)
        chunk_id = match.group(1) if match else f"QA-{len(chunks) + 1:03d}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                title=current_title,
                section=section,
                content=content,
                source_path=source_path,
                line_start=current_start,
                line_end=end_line,
            )
        )
        current_title = None
        current_start = None
        current_body = []

    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            flush(number - 1)
            section = line[3:].strip()
            continue

        if line.startswith("### "):
            flush(number - 1)
            current_title = line[4:].strip()
            current_start = number
            current_body = []
            continue

        if current_title is not None:
            current_body.append(line)

    flush(len(lines))
    return chunks


class KnowledgeBase:
    """Lazy-loading local retriever with a future vector-search seam."""

    def __init__(self, source_path: str | Path):
        self.source_path = Path(source_path).expanduser()
        self._mtime_ns: Optional[int] = None
        self._chunks: list[KnowledgeChunk] = []
        self._vectors: list[tuple[dict[str, float], float]] = []
        self._idf: dict[str, float] = {}

    def _ensure_loaded(self) -> None:
        if not self.source_path.exists():
            raise FileNotFoundError(f"Knowledge source not found: {self.source_path}")

        mtime_ns = self.source_path.stat().st_mtime_ns
        if self._mtime_ns == mtime_ns and self._chunks:
            return

        text = self.source_path.read_text(encoding="utf-8")
        chunks = parse_markdown_questions(text, str(self.source_path))
        if not chunks:
            raise ValueError(f"No Markdown question chunks found in {self.source_path}")

        document_frequency: Counter[str] = Counter()
        raw_vectors: list[Counter[str]] = []
        for chunk in chunks:
            counts = Counter(_tokens(chunk.search_text))
            raw_vectors.append(counts)
            document_frequency.update(counts.keys())

        document_count = len(chunks)
        self._idf = {
            term: math.log((document_count + 1) / (frequency + 1)) + 1.0
            for term, frequency in document_frequency.items()
        }

        vectors: list[tuple[dict[str, float], float]] = []
        for counts in raw_vectors:
            weighted = {
                term: (1.0 + math.log(count)) * self._idf[term]
                for term, count in counts.items()
            }
            norm = math.sqrt(sum(value * value for value in weighted.values()))
            vectors.append((weighted, norm))

        self._chunks = chunks
        self._vectors = vectors
        self._mtime_ns = mtime_ns

    def status(self) -> dict[str, Any]:
        """Return index state without failing when the source is absent."""
        exists = self.source_path.exists()
        if exists:
            self._ensure_loaded()
        return {
            "source_path": str(self.source_path),
            "exists": exists,
            "indexed_chunks": len(self._chunks),
            "source_modified_at": datetime.fromtimestamp(
                self.source_path.stat().st_mtime
            ).isoformat()
            if exists
            else None,
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.05,
    ) -> list[KnowledgeMatch]:
        """Return the highest-scoring question chunks for a query."""
        if not query or not query.strip():
            return []

        self._ensure_loaded()
        query_terms = _tokens(query)
        if not query_terms:
            return []

        query_counts = Counter(query_terms)
        query_vector = {
            term: (1.0 + math.log(count)) * self._idf.get(term, 0.0)
            for term, count in query_counts.items()
            if term in self._idf
        }
        query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
        if query_norm == 0:
            return []

        query_term_set = set(query_terms)
        matches: list[KnowledgeMatch] = []
        for chunk, (vector, norm) in zip(self._chunks, self._vectors):
            if norm == 0:
                continue
            dot_product = sum(
                query_weight * vector.get(term, 0.0)
                for term, query_weight in query_vector.items()
            )
            score = dot_product / (query_norm * norm)

            title_terms = set(_tokens(chunk.title))
            title_overlap = len(query_term_set & title_terms) / len(query_term_set)
            score += 0.15 * title_overlap

            if score >= min_score:
                matches.append(KnowledgeMatch(chunk=chunk, score=score))

        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[: max(1, min(top_k, 10))]
