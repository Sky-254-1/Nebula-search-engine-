"""Vector and keyword retrieval."""

import math
import re

from vector.embeddings import load_vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def keyword_score(query: str, text: str) -> float:
    q_tokens = set(re.findall(r"\w+", query.lower()))
    if not q_tokens:
        return 0.0
    t_tokens = set(re.findall(r"\w+", text.lower()))
    if not t_tokens:
        return 0.0
    overlap = len(q_tokens & t_tokens)
    return overlap / len(q_tokens)


def retrieve_chunks(
    query_vector: list[float],
    candidates: list[dict],
    query: str,
    top_k: int = 10,
    vector_weight: float = 0.7,
) -> list[dict]:
    scored = []
    for item in candidates:
        vec = load_vector(item["vector_path"])
        v_score = cosine_similarity(query_vector, vec)
        k_score = keyword_score(query, item["content"])
        hybrid = vector_weight * v_score + (1 - vector_weight) * k_score
        scored.append({**item, "vector_score": v_score, "keyword_score": k_score, "score": hybrid})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
