import re
from flask import Flask, render_template, request, jsonify
from classifier import predict_category
from database import initialize_database, save_ticket, get_tickets

app = Flask(__name__)
DEPARTMENTS = ["IT", "HR", "Finance", "Sales", "Marketing", "Operations"]
IMPACTS = ["Low", "Medium", "High"]

def predict_severity(text):
    text = text.lower()
    critical_words = ["server down", "entire company", "production down", "security breach"]
    high_words = ["urgent", "cannot work", "business stopped", "client meeting", "vpn not working"]
    medium_words = ["slow", "error", "problem", "issue"]
    for word in critical_words:
        if word in text:
            return "Critical"
    for word in high_words:
        if word in text:
            return "High"
    for word in medium_words:
        if word in text:
            return "Medium"
    return "Low"

def calculate_priority(severity, business_impact):
    if severity == "Critical" and business_impact == "High":
        return "P1"
    if severity == "High" and business_impact == "High":
        return "P1"
    if severity == "High":
        return "P2"
    if severity == "Medium":
        return "P3"
    return "P4"

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
        "index.html", result=result, error=error,
        tickets=get_tickets(), departments=DEPARTMENTS, impacts=IMPACTS
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

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
