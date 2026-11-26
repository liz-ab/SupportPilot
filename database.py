import sqlite3
from datetime import datetime

DATABASE = "tickets.db"

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                email TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                department TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                priority TEXT NOT NULL,
                business_impact TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL
            )
        """)

def save_ticket(ticket):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tickets (
                employee_name, email, title, description, department,
                category, severity, priority, business_impact,
                confidence, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket["employee_name"], ticket["email"], ticket["title"],
            ticket["description"], ticket["department"], ticket["category"],
            ticket["severity"], ticket["priority"], ticket["business_impact"],
            ticket["confidence"], "Open", datetime.now().isoformat(timespec="seconds")
        ))
        return cursor.lastrowid

def get_tickets(limit=None):
    with get_connection() as connection:
        if limit is None:
            rows = connection.execute("SELECT * FROM tickets ORDER BY ticket_id DESC").fetchall()
        else:
            rows = connection.execute("SELECT * FROM tickets ORDER BY ticket_id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Milestone 2: stored AI resolutions, agent feedback and system metrics
# ---------------------------------------------------------------------------
import json


def initialize_resolutions():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS resolutions (
                resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                summary TEXT,
                resolution_text TEXT NOT NULL,
                steps TEXT NOT NULL,
                documents TEXT NOT NULL,
                workflow TEXT NOT NULL,
                query TEXT,
                keywords TEXT,
                escalate INTEGER NOT NULL DEFAULT 0,
                low_confidence INTEGER NOT NULL DEFAULT 0,
                top_relevance REAL,
                response_time_ms REAL NOT NULL,
                outcome TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
            )
        """)


def save_resolution(ticket_id, result):
    """Store a pipeline result (PipelineResult.to_dict()) for a ticket, replacing any earlier one."""
    resolution, docs = result["resolution"], result["documents"]
    with get_connection() as connection:
        connection.execute("DELETE FROM resolutions WHERE ticket_id = ?", (ticket_id,))
        connection.execute("""
            INSERT INTO resolutions (
                ticket_id, status, mode, summary, resolution_text, steps, documents, workflow, query,
                keywords, escalate, low_confidence, top_relevance, response_time_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id, resolution["status"], resolution["mode"], resolution["summary"], resolution["text"],
            json.dumps(resolution["steps"]),
            json.dumps([{k: d[k] for k in ("id", "title", "category", "score", "last_updated")} for d in docs]),
            json.dumps(result["workflow"]), result["analysis"]["query"],
            json.dumps(result["analysis"]["keywords"]), int(resolution["escalate"]),
            int(resolution["low_confidence"]), docs[0]["score"] if docs else None,
            result["response_time_ms"], datetime.now().isoformat(timespec="seconds")))


def _decode(row):
    if row is None:
        return None
    item = dict(row)
    for key in ("steps", "documents", "workflow", "keywords"):
        item[key] = json.loads(item[key]) if item.get(key) else []
    item["escalate"] = bool(item["escalate"])
    item["low_confidence"] = bool(item["low_confidence"])
    return item


def get_resolution(ticket_id):
    with get_connection() as connection:
        return _decode(connection.execute(
            "SELECT * FROM resolutions WHERE ticket_id = ?", (ticket_id,)).fetchone())


def get_resolutions():
    with get_connection() as connection:
        return {row["ticket_id"]: _decode(row) for row in connection.execute("SELECT * FROM resolutions")}


def get_ticket(ticket_id):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def set_outcome(ticket_id, outcome):
    """Record whether the AI resolution solved the ticket ('Resolved') or it was escalated."""
    status = {"Resolved": "Resolved", "Escalated": "Escalated"}[outcome]
    with get_connection() as connection:
        updated = connection.execute(
            "UPDATE resolutions SET outcome = ? WHERE ticket_id = ?", (outcome, ticket_id)).rowcount
        if updated:
            connection.execute("UPDATE tickets SET status = ? WHERE ticket_id = ?", (status, ticket_id))
        return bool(updated)


def get_metrics():
    """System metrics calculated from stored data (nothing is hard-coded)."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT COUNT(*) AS total,
                   AVG(response_time_ms) AS avg_ms,
                   AVG(top_relevance) AS avg_relevance,
                   SUM(outcome = 'Resolved') AS resolved,
                   SUM(outcome = 'Escalated') AS escalated,
                   SUM(status = 'INSUFFICIENT_KNOWLEDGE') AS insufficient
            FROM resolutions
        """).fetchone()
    resolved, escalated = row["resolved"] or 0, row["escalated"] or 0
    judged = resolved + escalated
    return {
        "resolutions_generated": row["total"],
        "resolved": resolved, "escalated": escalated, "feedback_count": judged,
        "resolution_rate": round(resolved / judged, 4) if judged else None,
        "average_response_time_s": round(row["avg_ms"] / 1000, 3) if row["avg_ms"] is not None else None,
        "average_top_relevance": round(row["avg_relevance"], 4) if row["avg_relevance"] is not None else None,
        "insufficient_knowledge": row["insufficient"] or 0,
    }
