"""Step 2: knowledge-base retrieval (the R in RAG).

TfidfRetriever    TF-IDF + cosine similarity over whole articles.
SemanticRetriever Chunks articles and compares dense vectors (latent semantic analysis by default,
                  or a sentence-transformers model when RAG_EMBEDDING_MODEL is set and installed).
HybridRetriever   Weighted blend of both.
"""
import re
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config
from models.schemas import RetrievedDocument


def _article_text(article):
    return f"{article.title} {article.title} {' '.join(article.tags)} {article.content}"


def _chunks(article):
    """Split an article into step-level chunks, each prefixed with the title."""
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\d+\.)", article.content) if p.strip()]
    return [f"{article.title}. {part}" for part in parts] or [f"{article.title}. {article.content}"]


class _Base:
    name = "base"

    def __init__(self, articles, category_boost=None):
        self.articles = articles
        self.category_boost = config.CATEGORY_BOOST if category_boost is None else category_boost

    def scores(self, query):
        raise NotImplementedError

    def search(self, query, top_k=3, category=None):
        scores = np.array(self.scores(query), dtype=float)
        if category and self.category_boost:
            for i, article in enumerate(self.articles):
                if article.ticket_category == category:
                    scores[i] *= 1 + self.category_boost
        scores = np.clip(scores, 0.0, 1.0)
        order = scores.argsort()[::-1][:top_k]
        return [RetrievedDocument(
            id=self.articles[i].id, title=self.articles[i].title, category=self.articles[i].category,
            content=self.articles[i].content, score=float(scores[i]),
            last_updated=self.articles[i].last_updated) for i in order]


class TfidfRetriever(_Base):
    name = "tfidf"

    def __init__(self, articles, **kwargs):
        super().__init__(articles, **kwargs)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.vectors = self.vectorizer.fit_transform([_article_text(a) for a in articles])

    def scores(self, query):
        return cosine_similarity(self.vectorizer.transform([query]), self.vectors)[0]


class SemanticRetriever(_Base):
    name = "semantic"

    def __init__(self, articles, **kwargs):
        super().__init__(articles, **kwargs)
        self.chunk_owner, texts = [], []
        for index, article in enumerate(articles):
            for chunk in _chunks(article):
                self.chunk_owner.append(index)
                texts.append(chunk)
        self._encoder = None
        if config.EMBEDDING_MODEL:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer(config.EMBEDDING_MODEL)
                self.vectors = self._encoder.encode(texts, normalize_embeddings=True)
            except Exception:
                self._encoder = None
        if self._encoder is None:
            self.tfidf = TfidfVectorizer(stop_words="english", sublinear_tf=True)
            matrix = self.tfidf.fit_transform(texts)
            components = max(2, min(80, matrix.shape[0] - 1, matrix.shape[1] - 1))
            self.svd = TruncatedSVD(n_components=components, random_state=42)
            self.vectors = self.svd.fit_transform(matrix)

    def _encode(self, query):
        if self._encoder is not None:
            return self._encoder.encode([query], normalize_embeddings=True)
        return self.svd.transform(self.tfidf.transform([query]))

    def scores(self, query):
        chunk_scores = cosine_similarity(self._encode(query), self.vectors)[0]
        best = np.zeros(len(self.articles))
        for owner, score in zip(self.chunk_owner, chunk_scores):
            best[owner] = max(best[owner], score)
        return best


class HybridRetriever(_Base):
    name = "hybrid"

    def __init__(self, articles, weight=0.5, **kwargs):
        super().__init__(articles, **kwargs)
        self.weight = weight
        self.lexical = TfidfRetriever(articles, category_boost=0)
        self.semantic = SemanticRetriever(articles, category_boost=0)

    def scores(self, query):
        return self.weight * np.array(self.lexical.scores(query)) + \
            (1 - self.weight) * np.array(self.semantic.scores(query))


def build_retriever(articles, kind=None, **kwargs):
    kind = kind or config.RETRIEVER
    return {"tfidf": TfidfRetriever, "semantic": SemanticRetriever}.get(kind, HybridRetriever)(articles, **kwargs)
