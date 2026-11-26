import os
import tempfile
import unittest

import database
from rag.analyzer import analyze_ticket
from rag.generator import build_context, generate_resolution
from rag.knowledge_base import load_articles
from rag.pipeline import RagPipeline
from rag.retriever import TfidfRetriever

VPN_TICKET = {
    "id": "T-2023-4521", "title": "VPN Connection Failing on Corporate Network",
    "description": "Unable to connect to VPN since this morning. Error message: Connection timed out.",
    "category": "VPN", "priority": "P2", "severity": "High"}


class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = load_articles()
        cls.pipeline = RagPipeline(cls.articles)

    def test_knowledge_base_loaded(self):
        ids = {a.id for a in self.articles}
        self.assertTrue({"KB001", "KB002", "KB003"} <= ids)

    def test_analysis_extracts_keywords_and_query(self):
        analysis = analyze_ticket(VPN_TICKET)
        self.assertIn("vpn", analysis.keywords)
        self.assertIn("connection", analysis.query)

    def test_retriever_ranks_vpn_guide_first(self):
        results = TfidfRetriever(self.articles).search("vpn connection timeout", top_k=3, category="VPN")
        self.assertEqual(results[0].id, "KB001")

    def test_pipeline_returns_cited_steps(self):
        result = self.pipeline.run(VPN_TICKET)
        self.assertEqual(result.resolution.status, "OK")
        self.assertTrue(result.resolution.steps)
        self.assertTrue(all(s.source_id for s in result.resolution.steps))
        self.assertEqual([w.status for w in result.workflow], ["completed"] * 4)

    def test_insufficient_knowledge_when_nothing_matches(self):
        result = self.pipeline.run({"id": "x", "title": "zzz qqq", "description": "xyzzy plugh"})
        self.assertEqual(result.resolution.status, "INSUFFICIENT_KNOWLEDGE")
        self.assertEqual(result.workflow[3].status, "skipped")

    def test_context_contains_sources(self):
        docs = self.pipeline.run(VPN_TICKET).documents
        context = build_context(docs)
        self.assertIn("SOURCE: KB001", context)

    def test_generator_without_documents(self):
        analysis = analyze_ticket(VPN_TICKET)
        self.assertEqual(generate_resolution(VPN_TICKET, [], analysis).status, "INSUFFICIENT_KNOWLEDGE")


class MetricsTests(unittest.TestCase):
    def test_metrics_come_from_stored_data(self):
        original = database.DATABASE
        with tempfile.TemporaryDirectory() as folder:
            database.DATABASE = os.path.join(folder, "t.db")
            try:
                database.initialize_database()
                database.initialize_resolutions()
                empty = database.get_metrics()
                self.assertIsNone(empty["resolution_rate"])
                ticket = {"employee_name": "A", "email": "a@b.co", "title": "t", "description": "d",
                          "department": "IT", "category": "VPN", "severity": "Low", "priority": "P4",
                          "business_impact": "Low", "confidence": 0.9}
                ids = [database.save_ticket(ticket) for _ in range(4)]
                result = RagPipeline().run(VPN_TICKET).to_dict()
                for i in ids:
                    database.save_resolution(i, result)
                for i, outcome in zip(ids, ["Resolved", "Resolved", "Resolved", "Escalated"]):
                    database.set_outcome(i, outcome)
                metrics = database.get_metrics()
                self.assertEqual(metrics["resolution_rate"], 0.75)
                self.assertEqual(metrics["resolutions_generated"], 4)
            finally:
                database.DATABASE = original


if __name__ == "__main__":
    unittest.main()
