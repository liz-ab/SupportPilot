import os
import tempfile
import unittest

import database


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.original = database.DATABASE
        self.folder = tempfile.TemporaryDirectory()
        database.DATABASE = os.path.join(self.folder.name, "t.db")
        database.initialize_database()
        database.initialize_resolutions()
        from app import app
        self.client = app.test_client()

    def tearDown(self):
        database.DATABASE = self.original
        self.folder.cleanup()

    def _create(self):
        return self.client.post("/api/tickets", json={
            "employee_name": "Arun", "email": "arun@company.com", "department": "Sales",
            "business_impact": "High", "title": "VPN not working",
            "description": "I cannot connect to the company VPN, connection timed out."})

    def test_ticket_gets_resolution(self):
        response = self._create()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["category"], "VPN")
        self.assertEqual(data["resolution"]["status"], "OK")

    def test_feedback_updates_metrics(self):
        ticket_id = self._create().get_json()["ticket_id"]
        reply = self.client.post(f"/api/tickets/{ticket_id}/feedback", json={"outcome": "resolved"})
        self.assertEqual(reply.get_json()["metrics"]["resolution_rate"], 1.0)
        self.assertEqual(self.client.post(f"/api/tickets/{ticket_id}/feedback", json={"outcome": "x"}).status_code, 400)

    def test_knowledge_base_search(self):
        reply = self.client.get("/api/knowledge-base/search?q=printer paper jam")
        self.assertEqual(reply.get_json()[0]["id"], "KB021")

    def test_unknown_ticket(self):
        self.assertEqual(self.client.get("/api/tickets/999/resolution").status_code, 404)


if __name__ == "__main__":
    unittest.main()
