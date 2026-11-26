"""The complete RAG pipeline: analyse, retrieve, augment, generate."""
import logging
import time
import config
from models.schemas import PipelineResult, STAGES, WorkflowStage
from rag.analyzer import analyze_ticket
from rag.generator import build_context, generate_resolution, _insufficient
from rag.knowledge_base import load_articles
from rag.retriever import build_retriever

log = logging.getLogger("supportpilot.rag")


def update_status(stage, status):
    log.info("[%s] %s", stage, status)


class RagPipeline:
    def __init__(self, articles=None, retriever=None):
        self.articles = articles if articles is not None else load_articles()
        self.retriever = retriever or build_retriever(self.articles)

    def run(self, ticket, top_k=None, min_relevance=None):
        top_k = top_k or config.TOP_K
        min_relevance = config.MIN_RELEVANCE if min_relevance is None else min_relevance
        started = time.perf_counter()
        workflow = [WorkflowStage(key, name) for key, name in STAGES]
        stage = {s.key: s for s in workflow}

        def timed(key, function):
            node = stage[key]
            node.status = "running"
            update_status(node.name, "running")
            begun = time.perf_counter()
            try:
                value = function()
                node.status = "completed"
                return value
            except Exception:
                node.status = "failed"
                raise
            finally:
                node.duration_ms = round((time.perf_counter() - begun) * 1000, 2)
                update_status(node.name, node.status)

        analysis = timed("ticket_analysis", lambda: analyze_ticket(ticket))
        candidates = timed("knowledge_retrieval", lambda: self.retriever.search(
            analysis.query, top_k=top_k, category=analysis.category if config.CATEGORY_BOOST else None))
        documents = [d for d in candidates if d.score >= min_relevance]
        below = [d for d in candidates if d.score < min_relevance]

        if not documents:
            stage["context_augmentation"].status = "skipped"
            stage["response_generation"].status = "skipped"
            resolution, context = _insufficient(), ""
        else:
            context = timed("context_augmentation", lambda: build_context(documents))
            resolution = timed("response_generation",
                               lambda: generate_resolution(ticket, documents, analysis, context))
        return PipelineResult(
            analysis=analysis, documents=documents, context=context, resolution=resolution,
            workflow=workflow, response_time_ms=round((time.perf_counter() - started) * 1000, 2),
            below_threshold=below)


def run_rag_pipeline(ticket, retriever=None):
    """Convenience wrapper that mirrors the workshop example."""
    pipeline = RagPipeline(retriever=retriever) if retriever else RagPipeline()
    return pipeline.run(ticket)
