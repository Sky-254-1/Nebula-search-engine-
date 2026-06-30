"""Search result ranker with BM25, TF-IDF, freshness, domain authority, and engagement signals."""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Optional

from app.indexer.indexer import InvertedIndex, tokenize, stem_tokens

logger = logging.getLogger("nebula.indexer.ranker")

_AUTHORITY_DOMAINS: dict[re.Pattern, float] = {
    re.compile(r"\.edu(\.[a-z]{2})?$"): 2.0,
    re.compile(r"\.gov(\.[a-z]{2})?$"): 1.8,
    re.compile(r"\.org(\.[a-z]{2})?$"): 1.2,
    re.compile(r"\.mil(\.[a-z]{2})?$"): 1.5,
}


def domain_authority_boost(url: str) -> float:
    for pattern, boost in _AUTHORITY_DOMAINS.items():
        if pattern.search(url):
            return boost
    return 1.0


def freshness_boost(published_at: str | None, max_days: int = 730) -> float:
    if not published_at:
        return 0.5
    try:
        if "T" in published_at:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(published_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - dt).days
        if days_old < 0:
            return 1.0
        return math.exp(-days_old / max_days)
    except (ValueError, TypeError):
        return 0.5


class Ranker:
    """Combines multiple scoring signals into a normalized relevance score."""

    def __init__(
        self,
        index: InvertedIndex | None = None,
        freshness_weight: float = 0.15,
        authority_weight: float = 0.10,
        ctr_weight: float = 0.05,
        bm25_weight: float = 0.70,
    ):
        self._index = index
        self._freshness_weight = freshness_weight
        self._authority_weight = authority_weight
        self._ctr_weight = ctr_weight
        self._bm25_weight = bm25_weight
        self._ctr_data: dict[int, float] = {}

    @property
    def index(self) -> InvertedIndex | None:
        return self._index

    @index.setter
    def index(self, value: InvertedIndex | None):
        self._index = value

    def record_click(self, doc_id: int):
        current = self._ctr_data.get(doc_id, 0.0)
        self._ctr_data[doc_id] = current + 1.0

    def _normalize(self, scores: list[float]) -> list[float]:
        if not scores:
            return scores
        min_s, max_s = min(scores), max(scores)
        if max_s == min_s:
            return [0.5] * len(scores)
        return [(s - min_s) / (max_s - min_s) for s in scores]

    def score(
        self,
        query: str,
        doc_id: int,
        url: str | None = None,
        published_at: str | None = None,
    ) -> float:
        tokens = stem_tokens(tokenize(query))
        if not tokens or self._index is None:
            return 0.0

        bm25_scores = []
        for term in tokens:
            score = self._index.bm25(term, doc_id)
            bm25_scores.append(score)
        bm25 = sum(bm25_scores) / max(len(bm25_scores), 1)

        freshness = freshness_boost(published_at)
        authority = domain_authority_boost(url or "")
        ctr = self._ctr_data.get(doc_id, 0.0)
        ctr_norm = min(ctr / 100.0, 1.0)

        return (
            self._bm25_weight * bm25
            + self._freshness_weight * freshness
            + self._authority_weight * authority
            + self._ctr_weight * ctr_norm
        )

    def rank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 10,
    ) -> list[dict]:
        scored: list[tuple[float, dict, int]] = []
        for i, doc in enumerate(candidates):
            doc_id = doc.get("id") or doc.get("doc_id") or i
            s = self.score(
                query,
                doc_id=doc_id if isinstance(doc_id, int) else i,
                url=doc.get("url", ""),
                published_at=doc.get("published_at") or doc.get("crawled_at"),
            )
            scored.append((s, doc, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        raw_scores = [s for s, _, _ in scored]
        normalized = self._normalize(raw_scores)

        results = []
        for (score, doc, idx), norm_score in zip(scored[:top_k], normalized):
            results.append(
                {
                    **doc,
                    "score": round(float(score), 6),
                    "normalized_score": round(norm_score, 6),
                    "rank": len(results) + 1,
                }
            )
        return results

    def rank_hybrid(
        self,
        query: str,
        keyword_results: list[dict],
        vector_results: list[dict],
        keyword_weight: float = 0.4,
        vector_weight: float = 0.6,
        top_k: int = 10,
    ) -> list[dict]:
        combined: dict[int, dict] = {}

        for doc in keyword_results:
            doc_id = doc.get("id") or doc.get("doc_id")
            if doc_id is not None:
                doc["keyword_score"] = doc.get("score", 0.0)
                doc["vector_score"] = 0.0
                combined[doc_id] = doc

        for doc in vector_results:
            doc_id = doc.get("id") or doc.get("doc_id")
            if doc_id is not None:
                if doc_id in combined:
                    combined[doc_id]["vector_score"] = doc.get("score", 0.0)
                    combined[doc_id]["score"] = (
                        keyword_weight * combined[doc_id].get("keyword_score", 0.0)
                        + vector_weight * doc.get("score", 0.0)
                    )
                else:
                    doc["keyword_score"] = 0.0
                    doc["vector_score"] = doc.get("score", 0.0)
                    doc["score"] = vector_weight * doc.get("score", 0.0)
                    combined[doc_id] = doc

        scored = sorted(combined.values(), key=lambda x: x.get("score", 0.0), reverse=True)
        return self.rank(query, scored, top_k=top_k)


_ranker: Ranker | None = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker()
    return _ranker


ranker = get_ranker()
