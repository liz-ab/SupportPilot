import csv

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

correct = 0
total = 0
with open("data/severity_test_cases.csv", newline="", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        predicted = predict_severity(row["ticket_text"])
        total += 1
        correct += predicted == row["expected_severity"]
accuracy = correct / total * 100 if total else 0
print(f"Severity test accuracy: {correct}/{total} = {accuracy:.2f}%")
print("Target (85%) met:", "YES" if accuracy >= 85 else "NO")
