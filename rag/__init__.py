"""Retrieval-Augmented Generation components for SupportPilot (Milestone 2)."""
from rag.pipeline import RagPipeline

_pipeline = None


def get_pipeline(reload=False):
    global _pipeline
    if _pipeline is None or reload:
        _pipeline = RagPipeline()
    return _pipeline
