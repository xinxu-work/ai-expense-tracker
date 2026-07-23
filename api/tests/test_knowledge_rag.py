"""Tests for the local interview knowledge retriever."""

import tempfile
import unittest
from pathlib import Path

from knowledge_rag import KnowledgeBase, parse_markdown_questions


SAMPLE_MARKDOWN = """# Knowledge Base

## RAG fundamentals

### AI-001 — What is RAG?

**Interview answer:**

RAG retrieves relevant context and grounds the model response in trusted sources.

### AI-002 — How do you evaluate a RAG application?

**Interview answer:**

Evaluate retrieval quality, groundedness, citations, latency, and cost.
"""


class KnowledgeRagTests(unittest.TestCase):
    def test_parser_preserves_question_ids_and_lines(self):
        chunks = parse_markdown_questions(SAMPLE_MARKDOWN, "sample.md")

        self.assertEqual([chunk.chunk_id for chunk in chunks], ["AI-001", "AI-002"])
        self.assertEqual(chunks[0].section, "RAG fundamentals")
        self.assertIn("trusted sources", chunks[0].content)
        self.assertGreaterEqual(chunks[0].line_start, 1)
        self.assertGreaterEqual(chunks[0].line_end, chunks[0].line_start)

    def test_search_returns_relevant_answer_with_citation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "knowledge.md"
            source.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            knowledge_base = KnowledgeBase(source)

            matches = knowledge_base.search("How can I evaluate RAG retrieval and citations?")

            self.assertTrue(matches)
            self.assertEqual(matches[0].chunk.chunk_id, "AI-002")
            self.assertIn("knowledge.md", matches[0].chunk.citation())

    def test_status_reports_indexed_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "knowledge.md"
            source.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
            status = KnowledgeBase(source).status()

            self.assertTrue(status["exists"])
            self.assertEqual(status["indexed_chunks"], 2)


if __name__ == "__main__":
    unittest.main()
