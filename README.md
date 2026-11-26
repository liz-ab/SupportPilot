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

## Milestone 2: Knowledge retrieval and resolution generation

Every ticket is analysed, matched against the knowledge base and given a troubleshooting resolution (a Retrieval-Augmented Generation pipeline).

```
Ticket -> Analysis & query -> Knowledge-base retrieval -> Context augmentation -> Resolution (with citations)
```

| Part | File |
|---|---|
| Settings (thresholds, retriever, optional LLM) | `config.py` |
| Knowledge base (32 articles) and loader | `data/knowledge_base.json`, `rag/knowledge_base.py` |
| Ticket analysis and query generation | `rag/analyzer.py` |
| Retrieval: TF-IDF, semantic (chunked) and hybrid | `rag/retriever.py` |
| Context building and resolution generation | `rag/generator.py` |
| Pipeline with workflow status | `rag/pipeline.py` |
| Data classes | `models/schemas.py` |
| Retrieval evaluation | `evaluate_rag.py`, `data/retrieval_eval.csv` |

**Knowledge base.** Add articles to `data/knowledge_base.json`, drop `.md` or `.txt` files into `data/kb_docs/` (first line is the title), or use the Knowledge base page or `POST /api/knowledge-base`.

**Retrieval.** TF-IDF with cosine similarity is the default. `RAG_RETRIEVER=semantic` or `hybrid` switches to chunked dense vectors (latent semantic analysis, or a sentence-transformers model when `RAG_EMBEDDING_MODEL` is set and the package is installed). Articles below `RAG_MIN_RELEVANCE` (0.08) are dropped. If none remain, the ticket gets `INSUFFICIENT_KNOWLEDGE` and is flagged for escalation. The cut-off is lower than the 0.30 in the workshop example because TF-IDF scores on short tickets are low; it was chosen on the evaluation set.

**Resolution.** Without an LLM key the generator reuses the steps written in the retrieved articles and cites each one (`Source: KB001 – VPN Troubleshooting Guide`). Set `LLM_API_KEY` (and optionally `LLM_API_URL`, `LLM_MODEL`) to use any OpenAI-compatible chat endpoint with the prompt from the project brief. Only steps that cite a retrieved article are accepted; otherwise it falls back to the built-in generator. The LLM path has not been run against a live endpoint.

**Metrics** shown in the interface are calculated:
- Retrieval accuracy: share of test tickets where an accepted article is in the results (`python evaluate_rag.py`).
- Resolution rate: tickets marked Resolved divided by tickets marked Resolved or Escalated by agents.
- Average response time: measured for every pipeline run.

### Retrieval results

Measured on 61 real helpdesk tickets (`data/retrieval_eval.csv`; 53 answerable, 8 with no suitable article). The accepted articles were chosen by hand.

| Metric | Result |
|---|---|
| Retrieval accuracy (accepted article in top 3) | 96.2% |
| Top-1 accuracy | 77.4% |
| Correctly rejected unanswerable tickets | 0 of 8 |

The retriever settings were tuned on these same tickets, so the figures are optimistic. The system does not yet reject unrelated tickets reliably. Weak matches are flagged to the agent, and the knowledge base needs more articles for broader coverage.

### API

| Endpoint | Purpose |
|---|---|
| `POST /api/tickets` | Create a ticket; the response includes the resolution |
| `POST /api/tickets/<id>/resolve` | Re-run the pipeline for a ticket |
| `GET /api/tickets/<id>/resolution` | Stored resolution and workflow status |
| `POST /api/tickets/<id>/feedback` | `{"outcome": "resolved"}` or `"escalated"` |
| `POST /api/resolve` | Resolution for free text, nothing stored |
| `GET /api/metrics` | System metrics |
| `GET /api/knowledge-base`, `GET /api/knowledge-base/search?q=` | List or search articles |
| `POST /api/knowledge-base` | Add an article |

Run the tests with `python -m unittest discover -s tests -t .`.

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

- `app.py`: Flask routes, ticket processing, priority and resolution API.
- `labeling.py`: text cleaning, category rules and severity rules.
- `build_dataset.py`: builds `data/ticket_dataset.csv` from the raw sources.
- `train_model.py`: trains the classifier and writes the evaluation report.
- `classifier.py`: model loading and prediction.
- `evaluate_severity.py`: scores severity against the hand-labelled sample.
- `database.py`: SQLite table creation and ticket storage.
- `templates/index.html`, `static/style.css`, `static/dashboard.js`, `static/resolution.js`: web interface, dashboard, AI resolution and knowledge base pages.
- `data/ticket_dataset.csv`: cleaned training data with source column.
- `data/audit_sample.csv`: 120 hand-labelled tickets used only for evaluation.
- `data/dataset_summary.json`, `data/evaluation_report.json`: build and evaluation details.
- `models/ticket_classifier.pkl`: saved vectorizer and classifier.

## Known limitations

- Category labels are rule-derived because no public dataset labels these six categories directly.
- The hand-labelled sample is small (120 tickets), so measured accuracy has a wide margin of error.
- Severity is keyword-based and can miss context.
- Confidence is a probability estimate, not a guarantee.
- Unrelated tickets are not yet rejected reliably by retrieval (see Retrieval results).
- This is a prototype, not a production ticketing system.
