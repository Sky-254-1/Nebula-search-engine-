"""
Advanced Ranking Engine
Implements sophisticated ranking algorithms including BM25, TF-IDF,
and ML-based ranking.
"""

import logging
import math
from collections import Counter
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
    tfidf_score: float = 0.0
    
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
        
        # Model persistence
        self.model_version = "1.0.0"
        self.last_training_date = None
    
    def extract_features(
        self,
        query: str,
        document: dict,
        all_documents: list[dict],
        user_profile: Optional[dict] = None,
    ) -> RankingFeatures:
        """Extract all ranking features for a document"""
        self.bm25_ranker.index_documents(all_documents)
        
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
        
        # Freshness/recency score
        features.freshness_score = self._calculate_freshness(document)
        
        # Domain authority
        features.domain_authority = self._calculate_domain_authority(document)
        
        # Click-through rate (from historical data if available)
        features.click_through_rate = document.get('ctr', 0.0)
        
        # Personalization
        if user_profile:
            # Handle both dict and UserProfile objects
            if hasattr(user_profile, 'interests'):
                interests = user_profile.interests
                click_count = getattr(user_profile, 'click_count', 0)
            else:
                interests = user_profile.get('interests', [])
                click_count = user_profile.get('click_count', 0)
            
            doc_text = f"{document.get('title', '')} {document.get('snippet', '')}".lower()
            features.personalization_score = sum(
                1.0 for interest in interests if interest in doc_text
            )
            features.previous_clicks = click_count
        
        return features
    
    def _calculate_freshness(self, document: dict) -> float:
        """Calculate freshness score based on document date"""
        from datetime import datetime
        
        # Try to extract date from document
        pub_date = document.get('published_date') or document.get('created_at')
        if not pub_date:
            return 0.5  # Default for unknown dates
        
        try:
            if isinstance(pub_date, str):
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            elif isinstance(pub_date, datetime):
                pub_date = pub_date
            else:
                return 0.5
            
            days_old = (datetime.now(pub_date.tzinfo) - pub_date).days
            
            # Exponential decay: newer = higher score
            # 0 days = 1.0, 30 days = 0.5, 365 days = 0.1
            freshness = max(0.0, 1.0 * (0.95 ** days_old))
            return round(freshness, 3)
        except Exception:
            return 0.5
    
    def _calculate_domain_authority(self, document: dict) -> float:
        """Calculate domain authority score"""
        # In production, this would look up domain authority from a database
        # or use signals like backlinks, domain age, etc.
        
        url = document.get('url', '')
        
        # Simple heuristic for demonstration
        high_authority_domains = [
            'wikipedia.org', 'github.com', 'stackoverflow.com',
            'medium.com', 'dev.to', 'arxiv.org'
        ]
        
        for domain in high_authority_domains:
            if domain in url:
                return 0.9
        
        return 0.5  # Default authority
    
    def score(
        self,
        query: str,
        document: dict,
        all_documents: list[dict],
        user_profile: Optional[dict] = None,
    ) -> float:
        """Calculate final ML-based ranking score"""
        features = self.extract_features(query, document, all_documents, user_profile)
        
        # Normalize BM25 and TF-IDF scores to 0-1 range
        normalized_bm25 = min(features.bm25_score / 10.0, 1.0)
        normalized_tfidf = min(features.tfidf_score / 5.0, 1.0)
        
        # Position score (0-1 range)
        position_score = min(self.position_ranker.score(query, document) / 10.0, 1.0)
        
        # Weighted combination of features
        score = (
            normalized_bm25 * self.weights['bm25']
            + normalized_tfidf * self.weights['tfidf']
            + position_score * self.weights['position']
            + features.freshness_score * self.weights['freshness']
            + features.click_through_rate * self.weights['click_through']
            + features.personalization_score * self.weights['personalization']
        )
        
        # Apply domain authority boost
        score *= (0.8 + 0.2 * features.domain_authority)
        
        return round(score, 4)


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
    
    def __init__(self, personalization_engine=None):
        self.bm25_ranker = BM25Ranker()
        self.ml_ranker = MLRanker()
        self.diversity_ranker = DiversityRanker()
        self.personalization_engine = personalization_engine
        self.feature_stats = {
            'total_ranked': 0,
            'avg_score': 0.0,
            'score_distribution': [],
        }
    
    async def rank(
        self,
        query: str,
        results: list[dict],
        user_profile: Optional[dict] = None,
        enable_diversity: bool = True,
        enable_freshness: bool = True,
    ) -> list[dict]:
        """
        Apply hybrid ranking:
        1. Index documents for BM25
        2. Score with ML ranker
        3. Apply diversity
        4. Track statistics
        """
        if not results:
            return []
        
        # Index for BM25
        self.bm25_ranker.index_documents(results)
        self.ml_ranker.bm25_ranker = self.bm25_ranker
        
        # Score all results
        scored_results = []
        scores = []
        for result in results:
            score = self.ml_ranker.score(query, result, results, user_profile)
            scored_results.append((score, result))
            scores.append(score)
        
        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        ranked_results = [result for _, result in scored_results]
        
        # Apply diversity if enabled
        if enable_diversity and len(ranked_results) > 1:
            ranked_results = self.diversity_ranker.diversify(ranked_results, query)
        
        # Apply personalization if user profile provided and personalization engine available
        if user_profile and self.personalization_engine:
            for result in ranked_results:
                adjustment = self.personalization_engine.calculate_result_score_adjustment(
                    user_profile, result
                )
                result['final_score'] = min(1.0, result.get('final_score', 0.0) + adjustment)
                result['personalization_adjustment'] = adjustment
        else:
            # Set final scores without personalization
            for idx, result in enumerate(ranked_results):
                result['final_score'] = scored_results[idx][0] if idx < len(scored_results) else 0.0
        
        # Add rank positions
        for idx, result in enumerate(ranked_results):
            result['rank_position'] = idx + 1
        
        # Update statistics
        self._update_statistics(scores)
        
        return ranked_results
    
    def _update_statistics(self, scores: list[float]) -> None:
        """Update ranking statistics"""
        self.feature_stats['total_ranked'] += len(scores)
        if scores:
            avg = sum(scores) / len(scores)
            self.feature_stats['avg_score'] = (
                (self.feature_stats['avg_score'] + avg) / 2
                if self.feature_stats['avg_score'] > 0
                else avg
            )


# Global ranker instance
import re
from datetime import datetime
hybrid_ranker = HybridRanker()


# Model management for production learning-to-rank
class RankingModelManager:
    """Manage ranking model lifecycle and training"""
    
    def __init__(self, ml_ranker: Optional[MLRanker] = None):
        self.ml_ranker = ml_ranker or MLRanker()
        self.training_data: list[dict] = []
        self.model_metadata = {
            'version': self.ml_ranker.model_version,
            'last_training_date': None,
            'training_samples': 0,
            'feature_importance': {},
        }
    
    def record_training_sample(
        self,
        query: str,
        document: dict,
        features: RankingFeatures,
        clicked: bool,
    ) -> None:
        """Record a training sample for model improvement"""
        self.training_data.append({
            'query': query,
            'document': document,
            'features': features,
            'clicked': clicked,
        })
    
    def should_retrain(self, sample_threshold: int = 1000) -> bool:
        """Check if model should be retrained"""
        return len(self.training_data) >= sample_threshold
    
    def clear_training_data(self) -> None:
        """Clear training data after model update"""
        self.training_data.clear()
    
    def get_model_info(self) -> dict:
        """Get current model information"""
        return {
            'version': self.ml_ranker.model_version,
            'last_training': self.ml_ranker.last_training_date,
            'training_samples': len(self.training_data),
            'feature_weights': self.ml_ranker.weights,
            'needs_retraining': self.should_retrain(),
        }
    
    def update_weights(self, new_weights: dict[str, float]) -> None:
        """Update model weights (for A/B testing or retraining)"""
        self.ml_ranker.weights.update(new_weights)
        self.model_metadata['last_training_date'] = datetime.now().isoformat()


# Global model manager instance
model_manager = RankingModelManager(hybrid_ranker.ml_ranker)
