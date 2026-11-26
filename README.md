# SupportPilot – AI Ticket Resolution Agent

## Milestone 1: Ticket Processing & Classification

SupportPilot accepts IT support tickets, predicts a category, estimates severity, calculates priority, and stores submissions in SQLite.

## Dataset

`data/ticket_dataset.csv` holds 3,594 cleaned English tickets built from three public collections (no synthetic records):

| Source | Notes |
|---|---|
| IT incidents (Hugging Face) | Real service-desk incidents; the main source for VPN and Password |
| Helpdesk topics (Kaggle) | Pre-processed helpdesk tickets, used for Hardware and Password |
| Multi-language support tickets (Kaggle) | English IT/Technical Support queue only |

Category counts: Software 1,297 · Password 939 · Hardware 664 · System 350 · Network 192 · VPN 152.

Rebuild it with `python build_dataset.py` after placing the three raw CSV files in `data/raw/` (`it_incidents.csv`, `helpdesk_topics.csv`, `multilang_tickets.csv`). Raw files are not committed.

### Cleaning steps

1. Remove mail headers, addresses, URLs, ids, greetings and repeated titles.
2. Keep English tickets of 4–120 words and drop duplicates.
3. Drop tickets about unrelated business areas (medical, marketing, finance and similar).
4. Assign a category only when the ticket headline points to exactly one area (rules in `labeling.py`).
5. Where a source has its own label, keep the ticket only if it agrees with the rule label.

### Limitations

No public dataset provides labels for these six categories directly, so category labels come from the rules above (checked against source labels where available). A 120-ticket sample (`data/audit_sample.csv`) was labelled by hand to measure this. Severity labels are not provided by any source, so severity uses a rule engine.

## Results

Run `python train_model.py` to regenerate `data/evaluation_report.json`.

| Check | Result | Target |
|---|---|---|
| Category accuracy, held-out test (695 tickets) | 95.3% | 90% |
| Category accuracy, hand-labelled sample (on-topic tickets) | 86.2% | 90% |
| Category accuracy with key terms hidden | 70.2% | – |
| Severity accuracy, hand-labelled sample (120 tickets) | 79.2% | 85% |

The hand-labelled results are the most realistic. Category accuracy is above 85% but below the 90% target on that sample, and severity is below its 85% target. The audit sample is small, so these figures have a wide margin of error.

## Categories

Network, VPN, Password, Software, Hardware, System.

## Technologies

Python, Flask, Pandas, scikit-learn, TF-IDF, Logistic Regression, Joblib, SQLite, HTML, CSS and Chart.js.

## Setup on Windows / VS Code

1. Install Python and Git.
2. Clone the repository and open the folder in VS Code.
3. Select **Terminal → New Terminal**.
4. Create a virtual environment:

   `python -m venv venv`

5. Activate it in PowerShell:

   `.\venv\Scripts\Activate.ps1`

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Alternatively, use `venv\Scripts\python.exe` instead of `python` in the commands below.

6. Install dependencies:

   `python -m pip install -r requirements.txt`

7. Train the model and regenerate the evaluation report (the trained model is already included, so this step is optional):

   `python train_model.py`

8. Start the application:

   `python app.py`

9. Open `http://127.0.0.1:5000`.

## REST API

POST `/api/tickets` with JSON:

```json
{
  "employee_name": "Arun",
  "email": "arun@example.com",
  "title": "VPN not working",
  "description": "VPN is not connecting and I have an important client meeting.",
  "department": "Sales",
  "business_impact": "High"
}
```

The response includes ticket ID, predicted category, severity, priority, confidence and status. Confidence is the model's probability estimate, not a guarantee of correctness.

## Severity and priority

Severity comes from a keyword rule engine in `labeling.py` (Critical, High, Medium, Low). It covers outages, urgency and blocked work, and treats routine requests such as password resets as Low. Priority is calculated from severity and the business impact chosen on the form; Critical tickets are always P1. Run `python evaluate_severity.py` to score the engine against the hand-labelled sample.

## Project files

- `app.py`: Flask routes, ticket processing and priority.
- `labeling.py`: text cleaning, category rules and severity rules.
- `build_dataset.py`: builds `data/ticket_dataset.csv` from the raw sources.
- `train_model.py`: trains the classifier and writes the evaluation report.
- `classifier.py`: model loading and prediction.
- `evaluate_severity.py`: scores severity against the hand-labelled sample.
- `database.py`: SQLite table creation and ticket storage.
- `templates/index.html`, `static/style.css`, `static/dashboard.js`: web interface and dashboard.
- `data/ticket_dataset.csv`: cleaned training data with source column.
- `data/audit_sample.csv`: 120 hand-labelled tickets used only for evaluation.
- `data/dataset_summary.json`, `data/evaluation_report.json`: build and evaluation details.
- `models/ticket_classifier.pkl`: saved vectorizer and classifier.

## Known limitations

- Category labels are rule-derived because no public dataset labels these six categories directly.
- The hand-labelled sample is small (120 tickets), so measured accuracy has a wide margin of error.
- Severity is keyword-based and can miss context.
- Confidence is a probability estimate, not a guarantee.
- This is a Milestone 1 prototype, not a production ticketing system.
