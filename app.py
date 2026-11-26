import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import json
import os
from classifier import predict_category, predict_severity
from database import (
    initialize_database, initialize_resolutions, save_ticket, get_tickets, get_ticket, save_resolution,
    get_resolution, get_resolutions, set_outcome, get_metrics)
from rag import get_pipeline
from rag.knowledge_base import add_article, load_articles
import config

app = Flask(__name__)


def load_report():
    path = os.path.join("data", "evaluation_report.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


DEPARTMENTS = ["IT", "HR", "Finance", "Sales", "Marketing", "Operations"]
IMPACTS = ["Low", "Medium", "High"]

def calculate_priority(severity, business_impact):
    if severity == "Critical":
        return "P1"
    if severity == "High" and business_impact == "High":
        return "P1"
    if severity == "High":
        return "P2"
    if severity == "Medium":
        return "P3"
    return "P4"

def display_id(ticket_id, year=None):
    return f"T-{year or datetime.now().year}-{int(ticket_id):04d}"


def resolve_ticket(ticket):
    """Run the RAG pipeline for a stored ticket and save the outcome."""
    created = str(ticket.get("created_at") or "")[:4] or None
    result = get_pipeline().run({
        "id": display_id(ticket["ticket_id"], created), "title": ticket["title"],
        "description": ticket["description"], "category": ticket.get("category"),
        "severity": ticket.get("severity"), "priority": ticket.get("priority")}).to_dict()
    save_resolution(ticket["ticket_id"], result)
    return get_resolution(ticket["ticket_id"])


def current_metrics():
    """Live system metrics. Retrieval accuracy comes from the offline evaluation (evaluate_rag.py)."""
    metrics = get_metrics()
    path = config.RAG_REPORT_PATH
    metrics["retrieval_accuracy"] = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            metrics["retrieval_accuracy"] = json.load(handle).get("retrieval_accuracy")
    return metrics


def kb_summary():
    return [{"id": a.id, "title": a.title, "category": a.category, "ticket_category": a.ticket_category,
             "tags": a.tags, "content": a.content, "last_updated": a.last_updated} for a in load_articles()]


def process_ticket(data):
    required = ["employee_name", "email", "title", "description", "department"]
    for field in required:
        if not str(data.get(field, "")).strip():
            raise ValueError(f"{field.replace('_', ' ').title()} is required.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(data["email"]).strip()):
        raise ValueError("Enter a valid email address.")
    if data["department"] not in DEPARTMENTS:
        raise ValueError("Select a valid department.")
    impact = data.get("business_impact", "Medium")
    if impact not in IMPACTS:
        raise ValueError("Select a valid business impact.")

    full_text = f'{data["title"]}. {data["description"]}'
    category, confidence = predict_category(full_text)
    severity = predict_severity(full_text)
    priority = calculate_priority(severity, impact)

    ticket = {
        "employee_name": str(data["employee_name"]).strip(),
        "email": str(data["email"]).strip(),
        "title": str(data["title"]).strip(),
        "description": str(data["description"]).strip(),
        "department": data["department"],
        "category": category,
        "severity": severity,
        "priority": priority,
        "business_impact": impact,
        "confidence": confidence
    }
    ticket["ticket_id"] = save_ticket(ticket)
    ticket["status"] = "Open"
    ticket["resolution"] = resolve_ticket(ticket)
    return ticket

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    if request.method == "POST":
        try:
            result = process_ticket(request.form)
        except ValueError as exc:
            error = str(exc)
        except FileNotFoundError as exc:
            error = str(exc)
    return render_template(
        "index.html", result=result, error=error, form=request.form if error else {},
        tickets=get_tickets(), departments=DEPARTMENTS, impacts=IMPACTS, report=load_report(),
        resolutions=get_resolutions(), metrics=current_metrics(), kb=kb_summary(),
        latest_id=result["ticket_id"] if result else None
    )

@app.route("/api/tickets", methods=["POST"])
def create_ticket_api():
    if not request.is_json:
        return jsonify({"error": "Send a JSON request."}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body."}), 400
    try:
        result = process_ticket(data)
        result["confidence"] = round(result["confidence"] * 100, 2)
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 500

def _ticket_or_404(ticket_id):
    ticket = get_ticket(ticket_id)
    if ticket is None:
        return None, (jsonify({"error": "Ticket not found."}), 404)
    return ticket, None


@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket_api(ticket_id):
    ticket, error = _ticket_or_404(ticket_id)
    if error:
        return error
    ticket["resolution"] = get_resolution(ticket_id)
    return jsonify(ticket)


@app.route("/api/tickets/<int:ticket_id>/resolve", methods=["POST"])
def resolve_ticket_api(ticket_id):
    """Run (or re-run) the RAG pipeline for an existing ticket."""
    ticket, error = _ticket_or_404(ticket_id)
    if error:
        return error
    return jsonify(resolve_ticket(ticket))


@app.route("/api/tickets/<int:ticket_id>/resolution", methods=["GET"])
def get_resolution_api(ticket_id):
    resolution = get_resolution(ticket_id)
    if resolution is None:
        return jsonify({"error": "No resolution has been generated for this ticket."}), 404
    return jsonify(resolution)


@app.route("/api/tickets/<int:ticket_id>/feedback", methods=["POST"])
def feedback_api(ticket_id):
    data = request.get_json(silent=True) or {}
    outcome = str(data.get("outcome", "")).capitalize()
    if outcome not in ("Resolved", "Escalated"):
        return jsonify({"error": "outcome must be 'resolved' or 'escalated'."}), 400
    if not set_outcome(ticket_id, outcome):
        return jsonify({"error": "No resolution found for this ticket."}), 404
    return jsonify({"ticket_id": ticket_id, "outcome": outcome, "metrics": current_metrics()})


@app.route("/api/resolve", methods=["POST"])
def resolve_text_api():
    """Generate a resolution for free text without storing a ticket."""
    data = request.get_json(silent=True) or {}
    title, description = str(data.get("title", "")).strip(), str(data.get("description", "")).strip()
    if not (title or description):
        return jsonify({"error": "Provide a title or a description."}), 400
    text = f"{title}. {description}"
    category, confidence = predict_category(text)
    severity = predict_severity(text)
    result = get_pipeline().run({
        "id": "adhoc", "title": title, "description": description, "category": category,
        "severity": severity, "priority": data.get("priority")})
    payload = result.to_dict()
    payload["classification"] = {"category": category, "severity": severity, "confidence": confidence}
    return jsonify(payload)


@app.route("/api/metrics")
def metrics_api():
    return jsonify(current_metrics())


@app.route("/api/knowledge-base", methods=["GET"])
def list_kb_api():
    return jsonify(kb_summary())


@app.route("/api/knowledge-base/search")
def search_kb_api():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Provide a search query with ?q=."}), 400
    top_k = min(max(request.args.get("top_k", 5, type=int), 1), 20)
    results = get_pipeline().retriever.search(query, top_k=top_k)
    return jsonify([{"id": r.id, "title": r.title, "category": r.category, "score": round(r.score, 4),
                     "content": r.content} for r in results])


@app.route("/api/knowledge-base", methods=["POST"])
def add_kb_api():
    data = request.get_json(silent=True) or {}
    title, content = str(data.get("title", "")).strip(), str(data.get("content", "")).strip()
    if not title or not content:
        return jsonify({"error": "Title and content are required."}), 400
    article = add_article(title, str(data.get("category", "General")), content,
                          str(data.get("ticket_category", "")), list(data.get("tags", [])))
    get_pipeline(reload=True)
    return jsonify({"id": article.id, "title": article.title}), 201


@app.route("/health")
def health():
    return jsonify({"status": "ok"})

initialize_database()
initialize_resolutions()

if __name__ == "__main__":
    app.run(debug=True)
