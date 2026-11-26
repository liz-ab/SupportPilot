"""Plain data structures shared by the RAG pipeline, the database layer and the API."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional

STAGES = [
    ("ticket_analysis", "Ticket Analysis & Query Generation"),
    ("knowledge_retrieval", "Knowledge Base Retrieval"),
    ("context_augmentation", "Context Augmentation"),
    ("response_generation", "Response Generation"),
]


@dataclass
class Article:
    id: str
    title: str
    category: str
    content: str
    ticket_category: str = ""
    tags: List[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class TicketAnalysis:
    ticket_id: str
    category: Optional[str]
    severity: Optional[str]
    priority: Optional[str]
    keywords: List[str]
    query: str


@dataclass
class RetrievedDocument:
    id: str
    title: str
    category: str
    content: str
    score: float
    last_updated: str = ""


@dataclass
class ResolutionStep:
    number: int
    text: str
    source_id: str
    source_title: str


@dataclass
class Resolution:
    status: str                      # OK | INSUFFICIENT_KNOWLEDGE
    text: str
    steps: List[ResolutionStep] = field(default_factory=list)
    summary: str = ""
    mode: str = "knowledge-base"     # knowledge-base | llm
    escalate: bool = False
    low_confidence: bool = False


@dataclass
class WorkflowStage:
    key: str
    name: str
    status: str = "pending"          # pending | running | completed | failed | skipped
    duration_ms: float = 0.0


@dataclass
class PipelineResult:
    analysis: TicketAnalysis
    documents: List[RetrievedDocument]
    context: str
    resolution: Resolution
    workflow: List[WorkflowStage]
    response_time_ms: float
    below_threshold: List[RetrievedDocument] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
