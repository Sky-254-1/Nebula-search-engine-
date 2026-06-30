"""Document indexer with content extraction, tokenization, TF-IDF, and inverted index."""

import json
import logging
import math
import re
import string
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("nebula.indexer")
settings = get_settings()

_STOP_WORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "by", "with", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "shall", "should", "may", "might", "must", "it", "its",
    "this", "that", "these", "those", "i", "me", "my", "we", "our", "you",
    "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "not", "no", "nor", "so", "if", "then", "else", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "too", "very", "just",
    "about", "above", "after", "again", "against", "below", "between",
    "into", "through", "during", "before", "after", "up", "down", "out",
}


def tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def simple_stem(word: str) -> str:
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "i"
    if word.endswith("ves"):
        return word[:-3] + "f"
    if word.endswith("ing"):
        return word[:-3]
    if word.endswith("ed"):
        return word[:-2]
    if word.endswith("ly"):
        return word[:-2]
    if word.endswith("er"):
        return word[:-2]
    if word.endswith("est"):
        return word[:-3]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def stem_tokens(tokens: list[str]) -> list[str]:
    return [simple_stem(t) for t in tokens]


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text_from_html(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_text_from_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext == ".docx":
        return extract_text_from_docx(path)
    if ext in (".txt", ".md", ".rst"):
        return path.read_text(encoding="utf-8", errors="replace")
    if ext in (".htm", ".html", ".xhtml"):
        return extract_text_from_html(path.read_text(encoding="utf-8", errors="replace"))
    return path.read_text(encoding="utf-8", errors="replace")


class InvertedIndex:
    def __init__(self):
        self._postings: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
        self._doc_count: int = 0
        self._doc_lengths: dict[int, int] = {}
        self._doc_metadata: dict[int, dict] = {}

    @property
    def doc_count(self) -> int:
        return self._doc_count

    def add_document(self, doc_id: int, tokens: list[str], metadata: dict | None = None):
        self._doc_count += 1
        self._doc_lengths[doc_id] = len(tokens)
        if metadata:
            self._doc_metadata[doc_id] = metadata

        term_freqs = Counter(tokens)
        for term, freq in term_freqs.items():
            self._postings[term][doc_id].append(freq)

    def remove_document(self, doc_id: int):
        for term in list(self._postings.keys()):
            if doc_id in self._postings[term]:
                del self._postings[term][doc_id]
                if not self._postings[term]:
                    del self._postings[term]
        self._doc_lengths.pop(doc_id, None)
        self._doc_metadata.pop(doc_id, None)
        self._doc_count = max(0, self._doc_count - 1)

    def tf_idf(self, term: str, doc_id: int) -> float:
        if term not in self._postings or doc_id not in self._postings[term]:
            return 0.0
        tf = math.log(1 + sum(self._postings[term][doc_id]))
        df = len(self._postings[term])
        idf = math.log((self._doc_count + 1) / (df + 1)) + 1
        return tf * idf

    def bm25(self, term: str, doc_id: int, k1: float = 1.5, b: float = 0.75) -> float:
        if term not in self._postings or doc_id not in self._postings[term]:
            return 0.0
        tf = sum(self._postings[term][doc_id])
        dl = self._doc_lengths.get(doc_id, 1)
        avg_dl = (
            sum(self._doc_lengths.values()) / len(self._doc_lengths)
            if self._doc_lengths
            else 1
        )
        df = len(self._postings[term])
        idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1)
        return idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avg_dl))))

    def search(self, query_tokens: list[str], top_k: int = 10) -> list[tuple[int, float]]:
        scores: defaultdict[int, float] = defaultdict(float)
        for term in query_tokens:
            if term in self._postings:
                for doc_id in self._postings[term]:
                    scores[doc_id] += self.tf_idf(term, doc_id)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: Path):
        data = {
            "postings": {term: {str(doc_id): freqs for doc_id, freqs in docs.items()} for term, docs in self._postings.items()},
            "doc_count": self._doc_count,
            "doc_lengths": {str(k): v for k, v in self._doc_lengths.items()},
            "doc_metadata": {str(k): v for k, v in self._doc_metadata.items()},
        }
        path.write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "InvertedIndex":
        idx = cls()
        if not path.exists():
            return idx
        data = json.loads(path.read_text(encoding="utf-8"))
        idx._postings = defaultdict(
            lambda: defaultdict(list),
            {term: {int(doc_id): freqs for doc_id, freqs in docs.items()} for term, docs in data["postings"].items()},
        )
        idx._doc_count = data["doc_count"]
        idx._doc_lengths = {int(k): v for k, v in data.get("doc_lengths", {}).items()}
        idx._doc_metadata = {int(k): v for k, v in data.get("doc_metadata", {}).items()}
        return idx

    def get_metadata(self, doc_id: int) -> dict | None:
        return self._doc_metadata.get(doc_id)

    def total_terms(self) -> int:
        return sum(len(docs) for docs in self._postings.values())


class DocumentIndexer:
    """Indexes crawled documents using TF-IDF and integrates with the vector pipeline."""

    def __init__(self, index_path: Path | None = None):
        self._index_path = index_path or settings.storage_indexes / "inverted_index.json"
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index = InvertedIndex.load(self._index_path)
        self._documents: dict[int, dict] = {}

    @property
    def index(self) -> InvertedIndex:
        return self._index

    @property
    def document_count(self) -> int:
        return self._index.doc_count

    async def index_content(
        self,
        doc_id: int,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        text = normalize_text(content)
        tokens = tokenize(text)
        stemmed = stem_tokens(tokens)

        self._index.add_document(doc_id, stemmed, metadata)
        self._documents[doc_id] = {"content": text, "metadata": metadata or {}}
        self._save()

        return len(stemmed)

    async def index_html(
        self,
        doc_id: int,
        html: str,
        metadata: dict | None = None,
    ) -> int:
        text = extract_text_from_html(html)
        return await self.index_content(doc_id, text, metadata)

    async def index_file(self, doc_id: int, path: Path, metadata: dict | None = None) -> int:
        text = extract_text(path)
        return await self.index_content(doc_id, text, metadata)

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        tokens = stem_tokens(tokenize(query))
        return self._index.search(tokens, top_k=top_k)

    def remove(self, doc_id: int):
        self._index.remove_document(doc_id)
        self._documents.pop(doc_id, None)
        self._save()

    def get_document_text(self, doc_id: int) -> str | None:
        doc = self._documents.get(doc_id)
        return doc["content"] if doc else None

    def _save(self):
        self._index.save(self._index_path)

    def reload(self):
        self._index = InvertedIndex.load(self._index_path)


_indexer: DocumentIndexer | None = None


def get_indexer() -> DocumentIndexer:
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer


doc_indexer = get_indexer()
