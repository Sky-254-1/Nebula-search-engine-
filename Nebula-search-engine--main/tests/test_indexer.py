"""Indexer tests: text extraction, TF-IDF, BM25, inverted index, tokenization, freshness ranking."""

import math
import re
from collections import Counter, defaultdict


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"\w+", text)]


class TestTokenization:
    def test_simple_text(self):
        tokens = tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_removes_punctuation(self):
        tokens = tokenize("Hello, World!")
        assert tokens == ["hello", "world"]

    def test_lowercases(self):
        tokens = tokenize("HELLO")
        assert tokens == ["hello"]

    def test_empty_string(self):
        assert tokenize("") == []

    def test_special_characters(self):
        tokens = tokenize("price: $10.50")
        assert "price" in tokens
        assert "10" in tokens
        assert "50" in tokens


def compute_tf(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return {}
    counts = Counter(tokens)
    max_freq = max(counts.values())
    return {word: freq / max_freq for word, freq in counts.items()}


def compute_idf(documents: list[str]) -> dict[str, float]:
    n = len(documents)
    df: dict[str, int] = defaultdict(int)
    for doc in documents:
        for word in set(tokenize(doc)):
            df[word] += 1
    return {word: math.log((n + 1) / (count + 1)) + 1 for word, count in df.items()}


class TestTFIDFScoring:
    def test_tf_single_word(self):
        tf = compute_tf("hello hello world")
        assert tf["hello"] == 1.0
        assert tf["world"] == 0.5

    def test_tf_empty(self):
        assert compute_tf("") == {}

    def test_idf_common_words_lower_score(self):
        docs = ["the cat", "the dog", "the bird"]
        idf = compute_idf(docs)
        assert idf["the"] < idf["cat"]

    def test_idf_single_doc(self):
        docs = ["python programming"]
        idf = compute_idf(docs)
        assert idf["python"] > 0

    def test_tfidf_score(self):
        docs = ["python is great", "python is powerful", "java is different"]
        idf = compute_idf(docs)
        tf = compute_tf("python python java")
        score = sum(tf.get(w, 0) * idf.get(w, 0) for w in tf)
        assert score > 0


def bm25_score(query_tokens: list[str], doc_tokens: list[str], avg_doc_len: float, doc_len: float, n_docs: int, df: dict[str, int], k1: float = 1.5, b: float = 0.75) -> float:
    score = 0.0
    doc_counts = Counter(doc_tokens)
    for q in set(query_tokens):
        if q not in df:
            continue
        idf = math.log((n_docs - df[q] + 0.5) / (df[q] + 0.5) + 1)
        tf = doc_counts.get(q, 0)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
    return score


class TestBM25Scoring:
    def test_bm25_relevance(self):
        docs = ["python programming language", "java programming", "python is popular"]
        n_docs = len(docs)
        avg_len = sum(len(tokenize(d)) for d in docs) / n_docs
        df = {word: sum(1 for d in docs if word in set(tokenize(d))) for word in set(tokenize(" ".join(docs)))}

        scores = []
        for doc in docs:
            doc_tokens = tokenize(doc)
            scores.append(bm25_score(tokenize("python"), doc_tokens, avg_len, len(doc_tokens), n_docs, df))

        idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        assert idx[0] == 0 or idx[0] == 2

    def test_bm25_empty_query(self):
        docs = ["some content"]
        score = bm25_score([], tokenize("some content"), 3, 3, 1, {})
        assert score == 0.0


class TestInvertedIndex:
    def test_build_inverted_index(self):
        docs = [
            {"id": 1, "content": "python programming"},
            {"id": 2, "content": "java programming"},
        ]
        index: dict[str, list[int]] = defaultdict(list)
        for doc in docs:
            for word in set(tokenize(doc["content"])):
                index[word].append(doc["id"])

        assert index["python"] == [1]
        assert index["java"] == [2]
        assert index["programming"] == [1, 2]

    def test_search_via_inverted_index(self):
        index = {"python": [1, 3], "java": [2], "programming": [1, 2, 3]}

        def search(query: str) -> set[int]:
            tokens = tokenize(query)
            if not tokens:
                return set()
            results = None
            for t in tokens:
                doc_ids = set(index.get(t, []))
                if results is None:
                    results = doc_ids
                else:
                    results &= doc_ids
            return results or set()

        assert search("python programming") == {1, 3}
        assert search("java") == {2}
        assert search("unknown") == set()


class TestFreshnessRanking:
    def test_recent_documents_ranked_higher(self):
        from datetime import datetime, timedelta

        docs = [
            {"id": 1, "created_at": datetime.utcnow() - timedelta(days=10)},
            {"id": 2, "created_at": datetime.utcnow() - timedelta(days=1)},
            {"id": 3, "created_at": datetime.utcnow()},
        ]

        def freshness_score(doc, max_age_days=30):
            age = (datetime.utcnow() - doc["created_at"]).total_seconds()
            return max(0, 1 - age / (max_age_days * 86400))

        scores = [(d["id"], freshness_score(d)) for d in docs]
        scores.sort(key=lambda x: x[1], reverse=True)
        assert scores[0][0] == 3
        assert scores[-1][0] == 1

    def test_freshness_boost_combination(self):
        from datetime import datetime, timedelta

        docs = [
            {"id": 1, "created_at": datetime.utcnow() - timedelta(days=20), "relevance": 0.9},
            {"id": 2, "created_at": datetime.utcnow() - timedelta(days=1), "relevance": 0.7},
        ]

        def combined_score(doc):
            age_days = (datetime.utcnow() - doc["created_at"]).days
            freshness = max(0, 1 - age_days / 30)
            return doc["relevance"] * 0.7 + freshness * 0.3

        scores = [(d["id"], combined_score(d)) for d in docs]
        scores.sort(key=lambda x: x[1], reverse=True)
        assert scores[0][0] == 2


@pytest.mark.asyncio
async def test_indexer_pipeline_imports():
    from vector.pipeline import index_document
    from vector.chunking import chunk_text, estimate_tokens
    from vector.ingestion import extract_text, content_hash
    assert callable(index_document)
    assert callable(chunk_text)
    assert callable(estimate_tokens)
    assert callable(extract_text)
    assert callable(content_hash)


@pytest.mark.asyncio
async def test_chunking_function():
    from vector.chunking import chunk_text

    text = "word " * 300
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


@pytest.mark.asyncio
async def test_content_hash_deterministic():
    from vector.ingestion import content_hash

    h1 = content_hash("hello world")
    h2 = content_hash("hello world")
    assert h1 == h2
    assert h1 != content_hash("different")


@pytest.mark.asyncio
async def test_estimate_tokens():
    from vector.chunking import estimate_tokens
    assert estimate_tokens("hello world") == 2
    assert estimate_tokens("") == 1
