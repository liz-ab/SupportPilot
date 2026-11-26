"""Build the cleaned training dataset from the three public ticket collections in data/raw/.

Sources
  it_incidents.csv      real IT service-desk incidents (Hugging Face)
  helpdesk_topics.csv   pre-processed helpdesk tickets (Kaggle)
  multilang_tickets.csv multi-language support tickets (Kaggle), English rows only

Run:  python build_dataset.py
"""
import json
import os
import pandas as pd
from labeling import clean_text, is_english, is_off_domain, rule_category, rule_severity

RAW = os.path.join("data", "raw")
OUT = os.path.join("data", "ticket_dataset.csv")
SUMMARY = os.path.join("data", "dataset_summary.json")
MIN_WORDS = 4
MAX_WORDS = 120
PER_CLASS_CAP = 2500


def load_sources():
    frames = []

    inc = pd.read_csv(os.path.join(RAW, "it_incidents.csv"))
    frames.append(pd.DataFrame({
        "raw_text": inc["Issue Description"], "source": "IT incidents (Hugging Face)", "native": ""}))

    topics = pd.read_csv(os.path.join(RAW, "helpdesk_topics.csv"))
    frames.append(pd.DataFrame({
        "raw_text": topics["Document"], "source": "Helpdesk topics (Kaggle)",
        "native": topics["Topic_group"]}))

    multi = pd.read_csv(os.path.join(RAW, "multilang_tickets.csv"))
    multi = multi[(multi["language"] == "en") & multi["queue"].isin(["IT Support", "Technical Support"])]
    tag_cols = [f"tag_{i}" for i in range(1, 9)]
    multi_tags = multi[tag_cols].fillna("").agg("|".join, axis=1)
    frames.append(pd.DataFrame({
        "raw_text": multi["subject"].fillna("") + ". " + multi["body"].fillna(""),
        "source": "Multi-language tickets (Kaggle)", "native": multi_tags}))

    return pd.concat(frames, ignore_index=True)


# Where a source carries its own label, the rule label must agree with it.
NATIVE_TAGS = {
    "Network": {"Network"},
    "Hardware": {"Hardware"},
    "Software": {"Software", "Bug", "Crash", "Software Update", "Compatibility"},
    "System": {"System", "Server", "Outage", "Performance", "Crash", "Disruption"},
}
HELPDESK_GROUPS = {"Hardware": {"Hardware"}, "Password": {"Access"}}


def native_label_agrees(row):
    source, native, cat = row["source"], row["native"], row["category"]
    if source.startswith("Helpdesk topics"):
        return native in HELPDESK_GROUPS.get(cat, set())
    if source.startswith("Multi-language"):
        wanted = NATIVE_TAGS.get(cat)
        return True if wanted is None else bool(wanted & set(native.split("|")))
    return True


def main():
    df = load_sources()
    stats = {"raw_records": int(len(df))}

    df["text"] = df["raw_text"].map(clean_text)
    words = df["text"].str.split().str.len()
    df = df[(words >= MIN_WORDS) & (words <= MAX_WORDS)]
    stats["after_length_filter"] = int(len(df))

    df = df[df["text"].map(is_english)]
    stats["after_english_filter"] = int(len(df))

    df = df.drop_duplicates(subset="text")
    stats["after_deduplication"] = int(len(df))

    df = df[~df["text"].map(is_off_domain)]
    stats["after_off_domain_filter"] = int(len(df))

    df["category"] = df["text"].map(rule_category)
    df = df.dropna(subset=["category"])
    df = df[df.apply(native_label_agrees, axis=1)]
    stats["after_unambiguous_labeling"] = int(len(df))

    df["severity"] = df["text"].map(rule_severity)

    # Cap very large classes so the model is not dominated by one category.
    parts = [g.sample(min(len(g), PER_CLASS_CAP), random_state=42)
             for _, g in df.groupby("category")]
    df = pd.concat(parts).sample(frac=1, random_state=42).reset_index(drop=True)

    df[["text", "category", "severity", "source"]].to_csv(OUT, index=False)

    stats["final_records"] = int(len(df))
    stats["category_counts"] = df["category"].value_counts().to_dict()
    stats["severity_counts"] = df["severity"].value_counts().to_dict()
    stats["category_by_source"] = {
        c: g["source"].value_counts().to_dict() for c, g in df.groupby("category")}
    stats["synthetic_records"] = 0
    with open(SUMMARY, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
