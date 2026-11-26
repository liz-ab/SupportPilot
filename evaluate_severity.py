"""Score the severity rule engine against the hand-labelled audit tickets."""
import pandas as pd
from labeling import rule_severity

audit = pd.read_csv("data/audit_sample.csv")
predicted = audit["text"].map(rule_severity)
correct = int((predicted == audit["true_severity"]).sum())
accuracy = correct / len(audit) * 100
print(f"Severity accuracy on hand-labelled audit set: {correct}/{len(audit)} = {accuracy:.2f}%")
print(pd.crosstab(audit["true_severity"], predicted, rownames=["actual"], colnames=["predicted"]))
