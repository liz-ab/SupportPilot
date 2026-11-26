"""Central settings for SupportPilot. Values can be overridden with environment variables."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
KB_PATH = os.path.join(DATA_DIR, "knowledge_base.json")
KB_DOCS_DIR = os.path.join(DATA_DIR, "kb_docs")          # optional extra .md / .txt articles
RAG_REPORT_PATH = os.path.join(DATA_DIR, "rag_evaluation.json")
RETRIEVAL_EVAL_PATH = os.path.join(DATA_DIR, "retrieval_eval.csv")

# Retrieval. TF-IDF cosine scores on short tickets are low, so the cut-off was chosen on the labelled
# evaluation set (see evaluate_rag.py --compare) instead of the 0.30 used in the workshop example.
RETRIEVER = os.getenv("RAG_RETRIEVER", "tfidf")          # tfidf | semantic | hybrid
TOP_K = int(os.getenv("RAG_TOP_K", "3"))
MIN_RELEVANCE = float(os.getenv("RAG_MIN_RELEVANCE", "0.08"))
CATEGORY_BOOST = float(os.getenv("RAG_CATEGORY_BOOST", "0.3"))
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "")    # e.g. a sentence-transformers model name

# Optional LLM (any OpenAI-compatible chat completions endpoint). Without a key the
# built-in grounded generator is used.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "20"))
