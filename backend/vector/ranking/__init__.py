"""Result reranking."""

def rerank(results: list[dict], boost_recent: bool = True) -> list[dict]:
    if not boost_recent:
        return results
    ranked = []
    for i, item in enumerate(results):
        recency = 1.0 / (1 + i * 0.01)
        ranked.append({**item, "score": item.get("score", 0) * recency})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
