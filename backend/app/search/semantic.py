"""
Semantic Search Engine
Implements embedding-based semantic similarity search.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx
import numpy as np

from app.config import get_settings
from app.services.cache import cache_service

logger = logging.getLogger("nebula.search.semantic")
settings = get_settings()


class EmbeddingProvider:
    """Abstract embedding provider"""
    
    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embeddings (text-embedding-ada-002)"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    async def embed_text(self, text: str) -> list[float]:
        """Get embedding for single text"""
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return []
        
        # Check cache first
        cache_key = f"embedding:openai:{hash(text)}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text,
                        "model": self.model,
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                
                # Cache for future use
                await cache_service.set(cache_key, embedding, ttl=86400 * 7)  # 7 days
                
                return embedding
        
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return []
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts"""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": texts,
                        "model": self.model,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                embeddings = [item["embedding"] for item in data["data"]]
                
                # Cache individual embeddings
                for text, embedding in zip(texts, embeddings):
                    cache_key = f"embedding:openai:{hash(text)}"
                    await cache_service.set(cache_key, embedding, ttl=86400 * 7)
                
                return embeddings
        
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            return []


class OllamaEmbeddings(EmbeddingProvider):
    """Local Ollama embeddings"""
    
    def __init__(self, model: str = "nomic-embed-text", base_url: Optional[str] = None):
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    async def embed_text(self, text: str) -> list[float]:
        """Get embedding from Ollama"""
        cache_key = f"embedding:ollama:{self.model}:{hash(text)}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding", [])
                
                await cache_service.set(cache_key, embedding, ttl=86400 * 7)
                
                return embedding
        
        except Exception as e:
            logger.debug(f"Ollama embedding error: {e}")
            return []
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts"""
        tasks = [self.embed_text(text) for text in texts]
        return await asyncio.gather(*tasks)


class SemanticSearchEngine:
    """Semantic similarity search using embeddings"""
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or self._get_default_provider()
        self.indexed_embeddings = {}  # doc_id -> embedding
        self.indexed_documents = {}   # doc_id -> document
    
    def _get_default_provider(self) -> EmbeddingProvider:
        """Get default embedding provider"""
        # Try OpenAI first, fall back to Ollama
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIEmbeddings()
        return OllamaEmbeddings()
    
    async def index_documents(self, documents: list[dict]):
        """Index documents for semantic search"""
        texts = []
        doc_ids = []
        
        for i, doc in enumerate(documents):
            # Create searchable text
            text = f"{doc.get('title', '')} {doc.get('snippet', '')}".strip()
            if text:
                texts.append(text)
                doc_ids.append(i)
                self.indexed_documents[i] = doc
        
        if not texts:
            return
        
        # Get embeddings
        embeddings = await self.provider.embed_batch(texts)
        
        # Store embeddings
        for doc_id, embedding in zip(doc_ids, embeddings):
            if embedding:
                self.indexed_embeddings[doc_id] = np.array(embedding)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5,
    ) -> list[dict]:
        """
        Semantic search using query embedding.
        
        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)
        
        Returns:
            List of documents with similarity scores
        """
        if not query.strip():
            return []
        
        # Get query embedding
        query_embedding = await self.provider.embed_text(query)
        if not query_embedding:
            logger.warning("Failed to get query embedding")
            return []
        
        query_vec = np.array(query_embedding)
        
        # Calculate similarities
        similarities = []
        for doc_id, doc_embedding in self.indexed_embeddings.items():
            similarity = self._cosine_similarity(query_vec, doc_embedding)
            
            if similarity >= threshold:
                doc = self.indexed_documents[doc_id].copy()
                doc['semantic_score'] = similarity
                similarities.append((similarity, doc))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for _, doc in similarities[:top_k]]
    
    async def rerank(
        self,
        query: str,
        documents: list[dict],
        alpha: float = 0.5,
    ) -> list[dict]:
        """
        Re-rank documents using semantic similarity.
        
        Args:
            query: Search query
            documents: Documents to rerank
            alpha: Weight for semantic score (0-1, higher = more semantic weight)
        
        Returns:
            Re-ranked documents
        """
        # Index documents
        await self.index_documents(documents)
        
        # Get semantic scores
        semantic_results = await self.search(query, top_k=len(documents), threshold=0.0)
        
        # Create semantic score lookup
        semantic_scores = {
            doc.get('url', ''): doc.get('semantic_score', 0.0)
            for doc in semantic_results
        }
        
        # Combine with existing scores
        reranked = []
        for doc in documents:
            url = doc.get('url', '')
            semantic_score = semantic_scores.get(url, 0.0)
            
            # Combine semantic and keyword scores
            # Assume original order reflects keyword relevance
            keyword_score = 1.0 - (documents.index(doc) / len(documents))
            
            combined_score = alpha * semantic_score + (1 - alpha) * keyword_score
            
            doc_copy = doc.copy()
            doc_copy['semantic_score'] = semantic_score
            doc_copy['combined_score'] = combined_score
            
            reranked.append((combined_score, doc_copy))
        
        # Sort by combined score
        reranked.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for _, doc in reranked]


class QueryIntentClassifier:
    """Classify search query intent"""
    
    INTENTS = {
        'navigational': ['login', 'homepage', 'website', 'official', 'site'],
        'informational': ['what', 'how', 'why', 'when', 'where', 'who', 'tutorial', 'guide'],
        'transactional': ['buy', 'purchase', 'order', 'download', 'get', 'install'],
        'local': ['near me', 'nearby', 'location', 'address', 'directions'],
    }
    
    def classify(self, query: str) -> str:
        """Classify query intent"""
        query_lower = query.lower()
        
        # Check for intent keywords
        for intent, keywords in self.INTENTS.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        return 'informational'  # Default
    
    def get_intent_boost(self, query: str, document: dict) -> float:
        """Calculate intent-based boost for document"""
        intent = self.classify(query)
        
        # Apply intent-specific logic
        if intent == 'navigational':
            # Boost official/homepage results
            url = document.get('url', '').lower()
            if 'official' in url or url.endswith('/'):
                return 1.5
        
        elif intent == 'informational':
            # Boost tutorial/guide content
            title = document.get('title', '').lower()
            if any(word in title for word in ['tutorial', 'guide', 'how to']):
                return 1.3
        
        elif intent == 'transactional':
            # Boost e-commerce/download pages
            snippet = document.get('snippet', '').lower()
            if any(word in snippet for word in ['price', 'buy', 'download']):
                return 1.4
        
        return 1.0  # No boost


# Global instances
semantic_engine = SemanticSearchEngine()
intent_classifier = QueryIntentClassifier()
