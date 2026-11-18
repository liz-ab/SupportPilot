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

def get_tickets(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM tickets ORDER BY ticket_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
