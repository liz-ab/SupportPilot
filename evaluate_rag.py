"""Measure retrieval quality on data/retrieval_eval.csv and write data/rag_evaluation.json.

Each test ticket lists the knowledge-base articles a support agent would accept (expected_kb), or
NONE when the knowledge base has no suitable article.

Usage:  python evaluate_rag.py            evaluate the configured retriever
        python evaluate_rag.py --compare  compare tfidf, semantic and hybrid
"""
import json
import sys
import pandas as pd
import config
from classifier import predict_category
from rag.analyzer import analyze_ticket
from rag.knowledge_base import load_articles
from rag.retriever import build_retriever


def prepare(eval_df):
    rows = []
    for text in eval_df["ticket_text"]:
        try:
            category, _ = predict_category(text)
        except FileNotFoundError:
            category = None
        analysis = analyze_ticket({"id": "", "title": "", "description": text, "category": category})
        rows.append((analysis.query, category))
    return rows


def evaluate(retriever, eval_df, prepared, top_k=None, threshold=None):
    top_k = top_k or config.TOP_K
    threshold = config.MIN_RELEVANCE if threshold is None else threshold
    in_total = in_top1 = in_hit = out_total = out_deflected = 0
    for (query, category), expected in zip(prepared, eval_df["expected_kb"]):
        results = [r for r in retriever.search(query, top_k=top_k, category=category) if r.score >= threshold]
        if expected == "NONE":
            out_total += 1
            out_deflected += not results
            continue
        accepted = set(expected.split("|"))
        in_total += 1
        in_top1 += bool(results) and results[0].id in accepted
        in_hit += any(r.id in accepted for r in results)
    return {
        "in_scope_tickets": in_total, "out_of_scope_tickets": out_total,
        "top1_accuracy": round(in_top1 / in_total, 4), "retrieval_accuracy": round(in_hit / in_total, 4),
        "deflection_rate": round(out_deflected / out_total, 4) if out_total else None,
    }


def main():
    eval_df = pd.read_csv(config.RETRIEVAL_EVAL_PATH)
    articles = load_articles()
    prepared = prepare(eval_df)
    if "--compare" in sys.argv:
        for kind in ("tfidf", "semantic", "hybrid"):
            retriever = build_retriever(articles, kind)
            for threshold in (0.0, 0.2, 0.25, 0.3, 0.35, 0.4):
                print(kind, threshold, evaluate(retriever, eval_df, prepared, threshold=threshold))
        return
    retriever = build_retriever(articles)
    result = evaluate(retriever, eval_df, prepared)
    result.update({"retriever": retriever.name, "top_k": config.TOP_K, "min_relevance": config.MIN_RELEVANCE,
                   "category_boost": config.CATEGORY_BOOST, "knowledge_base_articles": len(articles),
                   "test_tickets": len(eval_df),
                   "note": "Tickets are real helpdesk tickets; the accepted articles were chosen by hand."})
    with open(config.RAG_REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
