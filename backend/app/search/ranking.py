"""
Advanced Ranking Engine
Implements sophisticated ranking algorithms including BM25, TF-IDF,
and ML-based ranking.
"""

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("nebula.search.ranking")


@dataclass
class RankingFeatures:
    """Features used for ranking"""
    
    # Content features
    term_frequency: float = 0.0
    inverse_document_frequency: float = 0.0
    bm25_score: float = 0.0
    
    # Position features
    title_match: bool = False
    snippet_match: bool = False
    url_match: bool = False
    
    # Quality signals
    domain_authority: float = 0.0
    freshness_score: float = 0.0
    click_through_rate: float = 0.0
    
    # User signals
    personalization_score: float = 0.0
    previous_clicks: int = 0
    
    # Semantic features
    semantic_similarity: float = 0.0
    query_intent_match: float = 0.0


class BM25Ranker:
    """BM25 ranking algorithm (industry standard)"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Controls term frequency saturation (1.2-2.0 typical)
            b: Controls length normalization (0-1, 0.75 typical)
        """
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0.0
        self.doc_count = 0
        self.doc_freq = Counter()  # Term -> number of docs containing it
        
    def index_documents(self, documents: list[dict]):
        """Index documents for BM25 scoring"""
        total_length = 0
        
        for doc in documents:
            # Extract text
            text = f"{doc.get('title', '')} {doc.get('snippet', '')}".lower()
            words = text.split()
            total_length += len(words)
            
            # Count term frequencies
            unique_terms = set(words)
            for term in unique_terms:
                self.doc_freq[term] += 1
        
        self.doc_count = len(documents)
        self.avg_doc_length = total_length / self.doc_count if self.doc_count > 0 else 0
    
    def score(self, query: str, document: dict) -> float:
        """Calculate BM25 score for document given query"""
        if self.doc_count == 0:
            return 0.0
        
        query_terms = query.lower().split()
        doc_text = f"{document.get('title', '')} {document.get('snippet', '')}".lower()
        doc_terms = doc_text.split()
        doc_length = len(doc_terms)
        
        # Count term frequencies in document
        term_freq = Counter(doc_terms)
        
        score = 0.0
        for term in query_terms:
            if term not in term_freq:
                continue
            
            # Term frequency component
            tf = term_freq[term]
            
            # Inverse document frequency
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue
            
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
            
            # Length normalization
            norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            
            # BM25 formula
            score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
        
        return score


class TFIDFRanker:
    """TF-IDF ranking"""
    
    def __init__(self):
        self.idf_cache = {}
        self.doc_count = 0
    
    def calculate_tf(self, term: str, text: str) -> float:
        """Calculate term frequency"""
        words = text.lower().split()
        if not words:
            return 0.0
        
        count = words.count(term.lower())
        return count / len(words)
    
    def calculate_idf(self, term: str, documents: list[dict]) -> float:
        """Calculate inverse document frequency"""
        if term in self.idf_cache:
            return self.idf_cache[term]
        
        doc_count = len(documents)
        if doc_count == 0:
            return 0.0
        
        # Count documents containing term
        docs_with_term = 0
        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('snippet', '')}".lower()
            if term.lower() in text:
                docs_with_term += 1
        
        if docs_with_term == 0:
            return 0.0
        
        idf = math.log(doc_count / docs_with_term)
        self.idf_cache[term] = idf
        return idf
    
    def score(self, query: str, document: dict, all_documents: list[dict]) -> float:
        """Calculate TF-IDF score"""
        query_terms = query.lower().split()
        doc_text = f"{document.get('title', '')} {document.get('snippet', '')}".lower()
        
        score = 0.0
        for term in query_terms:
            tf = self.calculate_tf(term, doc_text)
            idf = self.calculate_idf(term, all_documents)
            score += tf * idf
        
        return score


class PositionAwareRanker:
    """Ranking with position awareness (title, URL, snippet)"""
    
    def __init__(self):
        self.weights = {
            'title': 3.0,      # Title matches are very important
            'url': 2.0,        # URL matches indicate relevance
            'snippet': 1.0,    # Snippet matches are baseline
        }
    
    def score(self, query: str, document: dict) -> float:
        """Score based on where query terms appear"""
        query_terms = set(query.lower().split())
        score = 0.0
        
        # Check title
        title = document.get('title', '').lower()
        title_words = set(title.split())
        title_matches = len(query_terms & title_words)
        score += title_matches * self.weights['title']
        
        # Check URL
        url = document.get('url', '').lower()
        url_words = set(re.findall(r'\w+', url))
        url_matches = len(query_terms & url_words)
        score += url_matches * self.weights['url']
        
        # Check snippet
        snippet = document.get('snippet', '').lower()
        snippet_words = set(snippet.split())
        snippet_matches = len(query_terms & snippet_words)
        score += snippet_matches * self.weights['snippet']
        
        return score


class MLRanker:
    """Machine learning-based ranker (Learning to Rank)"""
    
    def __init__(self):
        self.bm25_ranker = BM25Ranker()
        self.tfidf_ranker = TFIDFRanker()
        self.position_ranker = PositionAwareRanker()
        
        # Feature weights (learned from data in production)
        self.weights = {
            'bm25': 0.35,
            'tfidf': 0.15,
            'position': 0.20,
            'freshness': 0.10,
            'click_through': 0.10,
            'personalization': 0.10,
        }
    
    def extract_features(
        self,
        query: str,
        document: dict,
        all_documents: list[dict],
        user_profile: Optional[dict] = None,
    ) -> RankingFeatures:
        """Extract all ranking features for a document"""
        features = RankingFeatures()
        
        # Content-based features
        features.bm25_score = self.bm25_ranker.score(query, document)
        features.tfidf_score = self.tfidf_ranker.score(query, document, all_documents)
        
        # Position features
        query_lower = query.lower()
        features.title_match = query_lower in document.get('title', '').lower()
        features.snippet_match = query_lower in document.get('snippet', '').lower()
        features.url_match = any(
            term in document.get('url', '').lower() for term in query_lower.split()
        )
        
        # Personalization
        if user_profile:
            interests = user_profile.get('interests', [])
            doc_text = f"{document.get('title', '')} {document.get('snippet', '')}".lower()
            features.personalization_score = sum(
                1.0 for interest in interests if interest in doc_text
            )
        
        return features
    
    def score(
        self,
        query: str,
        document: dict,
        all_documents: list[dict],
        user_profile: Optional[dict] = None,
    ) -> float:
        """Calculate final ML-based ranking score"""
        features = self.extract_features(query, document, all_documents, user_profile)
        
        # Weighted combination of features
        score = (
            features.bm25_score * self.weights['bm25']
            + features.tfidf_score * self.weights.get('tfidf', 0.15)
            + self.position_ranker.score(query, document) * self.weights['position']
            + features.click_through_rate * self.weights['click_through']
            + features.personalization_score * self.weights['personalization']
        )
        
        return score


class DiversityRanker:
    """Promote diversity in search results"""
    
    def __init__(self, diversity_weight: float = 0.3):
        self.diversity_weight = diversity_weight
    
    def diversify(self, results: list[dict], query: str, top_k: int = 10) -> list[dict]:
        """
        Re-rank results to promote diversity (avoid too similar results)
        Uses Maximal Marginal Relevance (MMR)
        """
        if len(results) <= 1:
            return results
        
        selected = []
        remaining = results.copy()
        
        # Start with highest scored result
        selected.append(remaining.pop(0))
        
        while remaining and len(selected) < top_k:
            best_score = -float('inf')
            best_idx = 0
            
            for idx, candidate in enumerate(remaining):
                # Calculate similarity to already selected results
                max_similarity = max(
                    self._similarity(candidate, selected_result)
                    for selected_result in selected
                )
                
                # MMR score: balance relevance and diversity
                # Higher score if dissimilar to selected results
                mmr_score = (1 - self.diversity_weight) - self.diversity_weight * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _similarity(self, doc1: dict, doc2: dict) -> float:
        """Calculate similarity between two documents (Jaccard similarity)"""
        text1 = f"{doc1.get('title', '')} {doc1.get('snippet', '')}".lower()
        text2 = f"{doc2.get('title', '')} {doc2.get('snippet', '')}".lower()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class HybridRanker:
    """Hybrid ranking combining multiple algorithms"""
    
    def __init__(self):
        self.bm25_ranker = BM25Ranker()
        self.ml_ranker = MLRanker()
        self.diversity_ranker = DiversityRanker()
    
    async def rank(
        self,
        query: str,
        results: list[dict],
        user_profile: Optional[dict] = None,
        enable_diversity: bool = True,
    ) -> list[dict]:
        """
        Apply hybrid ranking:
        1. Index documents for BM25
        2. Score with ML ranker
        3. Apply diversity
        """
        if not results:
            return []
        
        # Index for BM25
        self.bm25_ranker.index_documents(results)
        self.ml_ranker.bm25_ranker = self.bm25_ranker
        
        # Score all results
        scored_results = []
        for result in results:
            score = self.ml_ranker.score(query, result, results, user_profile)
            scored_results.append((score, result))
        
        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        ranked_results = [result for _, result in scored_results]
        
        # Apply diversity
        if enable_diversity:
            ranked_results = self.diversity_ranker.diversify(ranked_results, query)
        
        return ranked_results


# Global ranker instance
import re
hybrid_ranker = HybridRanker()
