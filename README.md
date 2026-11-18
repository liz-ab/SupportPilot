# SupportPilot – AI Ticket Resolution Agent

## Milestone 1: Ticket Processing & Classification

SupportPilot accepts IT support tickets, predicts a category, estimates severity, calculates priority, and stores submissions in SQLite.

## Dataset and data provenance

The file `data/ticket_dataset.csv` contains 3,216 records across the six project categories:

- **Kaggle-derived:** 1,716 selected records from the user-provided `customer_support_tickets.csv`. The selected source subjects were Network problem, Software bug, Installation support, Hardware issue, Display issue, and Peripheral compatibility. These were mapped to Network, Software, and Hardware.
- **Synthetic:** 1,500 supplementary training records for VPN, Password, and System, because the uploaded Kaggle file did not provide these as separate reliable labels.

The `data_source` column identifies every record as `Kaggle` or `Synthetic`. The `source_subject` column retains the original subject or identifies a generated example. Synthetic rows are not presented as Kaggle data.

The Kaggle dataset contains customer names, email addresses, demographic fields, product metadata and other columns that are not used by this classifier. Only the selected ticket text and mapped category are retained in the training CSV.

## Data cleaning and preprocessing

`classifier.py` contains the same preprocessing function used by training and prediction. It:

1. Converts text to lowercase.
2. Removes template placeholders such as `{product_purchased}`.
3. Removes URLs and email addresses.
4. Removes punctuation while retaining letters and digits.
5. Normalizes repeated whitespace.
6. The training script drops empty/very short rows and duplicate cleaned ticket text.

TF-IDF is fitted only on the training partition. The model uses unigram TF-IDF with sublinear term frequency and Logistic Regression (`C=2.0`, `class_weight="balanced"`). The split is stratified, 80:20, with `random_state=42`.

**Important data-quality limitation:** The Kaggle dataset's subject labels do not consistently agree with the free-text descriptions. Some descriptions contain unrelated or contradictory text. Text cleaning can remove formatting noise, but cannot reliably correct incorrect labels or rewrite unrelated content. Therefore, the Kaggle-only test accuracy is the most important real-source metric and remains below the 90% target.

## Categories

Network, VPN, Password, Software, Hardware, System.

## Technologies

Python, Flask, Pandas, scikit-learn, TF-IDF, Logistic Regression, Joblib, SQLite, HTML and Bootstrap.

## Setup on Windows / VS Code

1. Install Python and Git.
2. Extract the ZIP and open the extracted `SupportPilot_Milestone1_Kaggle` folder in VS Code.
3. Select **Terminal → New Terminal**.
4. Create a virtual environment:

   `python -m venv venv`

5. Activate it in PowerShell:

   `.\venv\Scripts\Activate.ps1`

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Alternatively, use `venv\Scripts\python.exe` instead of `python` in the commands below.

6. Install dependencies:

   `python -m pip install -r requirements.txt`

7. Train the model and regenerate the evaluation report:

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

## Evaluation results

The latest training run produced these measured results on the fixed stratified 80:20 split:

| Evaluation subset | Test records | Accuracy |
|---|---:|---:|
| Mixed Kaggle + synthetic test set | 644 | 67.70% |
| **Kaggle-only test subset** | **344** | **39.53%** |
| Synthetic-only test subset | 300 | 100.00% |

The 100% synthetic-only result is expected to be easier and is **not** evidence of real-world performance. Do not present the mixed or synthetic-only score as real-world accuracy. The 90% classification target is **not met** on the Kaggle-only test subset. The full per-class report and confusion matrix are in `data/evaluation_report.json`.

These results are a reproducible baseline, not a claim that the model generalizes well to real enterprise tickets. A better real-world score requires a cleaner, correctly labelled IT-ticket dataset, especially for Network, Software and Hardware.

## Severity and priority

Severity is assigned by the simple keyword rules in `app.py` (Critical → High → Medium → Low). Priority is calculated separately using severity and business impact. The small rule-based severity test file is a functional check, not proof of broad accuracy.

## Project files

- `app.py`: Flask routes, ticket processing, severity and priority.
- `train_model.py`: data cleaning, train/test split, TF-IDF training and evaluation.
- `classifier.py`: shared text preprocessing, model loading and prediction.
- `database.py`: SQLite table creation and ticket storage.
- `templates/index.html`: Bootstrap interface.
- `data/ticket_dataset.csv`: labelled Kaggle-derived and synthetic training records, with provenance columns.
- `data/severity_test_cases.csv`: small severity evaluation set.
- `evaluate_severity.py`: severity evaluation script.
- `data/evaluation_report.json`: actual metrics from the latest training run.
- `models/ticket_classifier.pkl`: saved TF-IDF vectorizer and Logistic Regression model.

## Limitations to explain to your mentor

- The Kaggle source is a general customer-support dataset, not a clean enterprise IT helpdesk dataset.
- Kaggle labels were mapped from subject names, but some descriptions do not match those subjects.
- VPN, Password and System training records are synthetic because the source does not provide those labels separately.
- The Kaggle-only held-out accuracy is 39.53%, below the 90% target.
- Severity is keyword-based and can miss context.
- Confidence is not a guarantee of correctness.
- This is a Milestone 1 prototype, not a production-ready ticketing system.
