"""Step 1: understand the ticket and build the knowledge-base search query."""
import re
from labeling import clean_text
from models.schemas import TicketAnalysis

POSSIBLE_KEYWORDS = [
    "vpn", "network", "firewall", "authentication", "timeout", "connection", "dns", "password",
    "wifi", "login", "locked", "mfa", "outlook", "email", "install", "license", "crash", "error",
    "printer", "laptop", "monitor", "keyboard", "battery", "server", "outage", "slow", "disk",
    "update", "windows", "certificate", "citrix", "usb", "headset", "camera", "stolen", "malware",
]


def extract_keywords(text):
    found = []
    for keyword in POSSIBLE_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}", text):
            found.append(keyword)
    return found


def analyze_ticket(ticket):
    """Return keywords plus a search query for a ticket dict.

    The ticket needs `title` and `description`; `category`, `severity` and `priority` come from the
    Milestone 1 classifier when available.
    """
    raw = f'{ticket.get("title", "")} {ticket.get("description", "")}'.lower()
    keywords = extract_keywords(raw)
    cleaned = clean_text(raw) or raw
    # Query generation: ticket text plus the keywords and predicted category.
    query = " ".join([cleaned] + keywords + [str(ticket.get("category") or "")]).strip()
    return TicketAnalysis(
        ticket_id=str(ticket.get("id", "")),
        category=ticket.get("category"),
        severity=ticket.get("severity"),
        priority=ticket.get("priority"),
        keywords=keywords,
        query=query,
    )
