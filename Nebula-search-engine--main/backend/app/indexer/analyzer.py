"""Text analyzer: language detection, keyword/entity extraction, summarization, sentiment."""

import logging
import math
import re
from collections import Counter
from typing import Optional

from app.indexer.indexer import tokenize, stem_tokens, normalize_text

logger = logging.getLogger("nebula.indexer.analyzer")

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+\.[a-zA-Z]{2,}[^\s<>\"']*")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)

_LANG_SIGNATURES: dict[str, set[str]] = {
    "en": {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out"},
    "es": {"el", "la", "los", "las", "del", "para", "con", "por", "como", "más", "pero", "sus", "que", "una", "son"},
    "fr": {"le", "la", "les", "des", "pour", "avec", "dans", "sur", "par", "pas", "plus", "sont", "mais", "cette", "être"},
    "de": {"der", "die", "das", "und", "mit", "von", "für", "auf", "nicht", "auch", "sind", "wird", "eine", "dem", "sein"},
    "it": {"il", "la", "le", "gli", "del", "della", "con", "per", "che", "non", "sono", "una", "era", "anche", "nel"},
    "pt": {"o", "a", "os", "as", "para", "com", "por", "como", "mais", "mas", "são", "uma", "era", "seu", "seus"},
    "nl": {"de", "het", "een", "van", "met", "voor", "niet", "ook", "zijn", "wordt", "heeft", "maar", "naar", "dan", "nog"},
    "ru": {"и", "в", "на", "с", "не", "что", "по", "для", "как", "от", "это", "но", "она", "они", "было"},
}

_POSITIVE_WORDS: set[str] = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic", "outstanding",
    "superb", "brilliant", "positive", "beautiful", "love", "happy", "perfect",
    "best", "awesome", "nice", "helpful", "useful", "impressive", "remarkable",
    "splendid", "delightful", "pleased", "satisfied", "recommended", "success",
    "beneficial", "advantage", "profit", "gain", "improve", "better",
}

_NEGATIVE_WORDS: set[str] = {
    "bad", "terrible", "awful", "horrible", "dreadful", "poor", "worst",
    "hate", "ugly", "disgusting", "disappointing", "mediocre", "inferior",
    "useless", "broken", "defective", "failure", "problem", "issue", "error",
    "flawed", "damaged", "harmful", "dangerous", "waste", "fake", "scam",
    "regret", "unfortunate", "negative", "annoying", "frustrating", "expensive",
}


def detect_language(text: str) -> str:
    if not text.strip():
        return "unknown"
    tokens = set(tokenize(text))
    best_lang = "unknown"
    best_score = 0
    for lang, sig in _LANG_SIGNATURES.items():
        score = len(tokens & sig)
        if score > best_score:
            best_score = score
            best_lang = lang
    return best_lang


def extract_keywords(text: str, top_k: int = 10) -> list[tuple[str, float]]:
    tokens = stem_tokens(tokenize(text))
    if not tokens:
        return []
    freqs = Counter(tokens)
    max_freq = max(freqs.values()) if freqs else 1
    total = len(tokens)
    keywords = []
    for word, freq in freqs.most_common(top_k * 2):
        tf = freq / total
        idf = math.log((total + 1) / (freq + 1)) + 1
        score = tf * idf
        keywords.append((word, score))
    keywords.sort(key=lambda x: x[1], reverse=True)
    return keywords[:top_k]


def extract_entities(text: str) -> dict[str, list[str]]:
    entities: dict[str, list[str]] = {
        "emails": list(set(_EMAIL_RE.findall(text))),
        "urls": list(set(_URL_RE.findall(text))),
        "phones": list(set(_PHONE_RE.findall(text))),
    }
    return entities


def summarize(text: str, max_sentences: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= max_sentences:
        return text.strip()

    tokens_per_sentence = [tokenize(s) for s in sentences]
    word_freq: Counter[str] = Counter()
    for toks in tokens_per_sentence:
        word_freq.update(toks)

    scored: list[tuple[float, str, int]] = []
    for i, (sentence, toks) in enumerate(zip(sentences, tokens_per_sentence)):
        if not toks:
            continue
        score = sum(word_freq.get(t, 0) for t in toks) / len(toks)
        scored.append((score, sentence.strip(), i))

    scored.sort(key=lambda x: (x[0], -x[2]), reverse=True)
    top = scored[:max_sentences]
    top.sort(key=lambda x: x[2])

    return " ".join(s[1] for s in top)


def analyze_sentiment(text: str) -> dict:
    tokens = set(tokenize(text))
    pos_count = len(tokens & _POSITIVE_WORDS)
    neg_count = len(tokens & _NEGATIVE_WORDS)
    total = pos_count + neg_count
    if total == 0:
        return {"sentiment": "neutral", "score": 0.0, "positive": 0, "negative": 0}

    score = (pos_count - neg_count) / total
    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "score": round(score, 4),
        "positive": pos_count,
        "negative": neg_count,
    }


class TextAnalyzer:
    """Comprehensive text analysis: language, keywords, entities, summary, sentiment."""

    def analyze(self, text: str, max_keywords: int = 10, max_summary_sentences: int = 3) -> dict:
        normalized = normalize_text(text)
        return {
            "language": detect_language(normalized),
            "keywords": extract_keywords(normalized, top_k=max_keywords),
            "entities": extract_entities(normalized),
            "summary": summarize(normalized, max_sentences=max_summary_sentences),
            "sentiment": analyze_sentiment(normalized),
            "word_count": len(normalized.split()),
            "char_count": len(normalized),
        }


_analyzer: TextAnalyzer | None = None


def get_analyzer() -> TextAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = TextAnalyzer()
    return _analyzer


text_analyzer = get_analyzer()
