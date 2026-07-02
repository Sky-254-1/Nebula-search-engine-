"""
Advanced Indexing Engine
Manages document indexing, inverted indices, and fast lookups.
"""

import asyncio
import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.cache import cache_service

logger = logging.getLogger("nebula.search.indexing")


@dataclass
class IndexedDocument:
    """Indexed document structure"""
    
    doc_id: str
    title: str
    content: str
    url: str
    source: str
    indexed_at: datetime
    metadata: dict = None
    
    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "indexed_at": self.indexed_at.isoformat(),
            "metadata": self.metadata or {},
        }


class Tokenizer:
    """Text tokenization and normalization"""
    
    def __init__(self):
        # Common stop words to filter out
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
        }
    
    def tokenize(self, text: str, remove_stop_words: bool = True) -> list[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Input text
            remove_stop_words: Whether to filter stop words
        
        Returns:
            List of tokens
        """
        # Lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words
        tokens = text.split()
        
        # Filter stop words
        if remove_stop_words:
            tokens = [t for t in tokens if t not in self.stop_words]
        
        # Filter short tokens
        tokens = [t for t in tokens if len(t) > 2]
        
        return tokens
    
    def stem(self, word: str) -> str:
        """
        Simple stemming (Porter stemmer-lite).
        For production, use nltk or similar.
        """
        # Remove common suffixes
        suffixes = ['ing', 'ed', 'ly', 'er', 'est', 's']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        return word


class InvertedIndex:
    """Inverted index for fast text search"""
    
    def __init__(self):
        # term -> {doc_id: [positions]}
        self.index = defaultdict(lambda: defaultdict(list))
        
        # doc_id -> document
        self.documents = {}
        
        # term -> document_frequency
        self.doc_freq = defaultdict(int)
        
        # Total documents
        self.doc_count = 0
        
        self.tokenizer = Tokenizer()
    
    async def add_document(self, doc: IndexedDocument):
        """Add document to index"""
        doc_id = doc.doc_id
        
        # Store document
        self.documents[doc_id] = doc
        self.doc_count += 1
        
        # Tokenize content
        text = f"{doc.title} {doc.content}"
        tokens = self.tokenizer.tokenize(text)
        
        # Build inverted index
        seen_terms = set()
        for position, token in enumerate(tokens):
            # Add to inverted index
            self.index[token][doc_id].append(position)
            
            # Track document frequency
            if token not in seen_terms:
                self.doc_freq[token] += 1
                seen_terms.add(token)
        
        # Cache document
        cache_key = f"index:doc:{doc_id}"
        await cache_service.set(cache_key, doc.to_dict(), ttl=3600)
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        use_stemming: bool = False,
    ) -> list[IndexedDocument]:
        """
        Search using inverted index.
        
        Args:
            query: Search query
            limit: Max results
            use_stemming: Whether to apply stemming
        
        Returns:
            List of matching documents
        """
        # Tokenize query
        query_tokens = self.tokenizer.tokenize(query)
        
        if not query_tokens:
            return []
        
        # Apply stemming if requested
        if use_stemming:
            query_tokens = [self.tokenizer.stem(t) for t in query_tokens]
        
        # Find documents containing query terms
        doc_scores = defaultdict(float)
        
        for token in query_tokens:
            if token in self.index:
                # Calculate IDF
                df = self.doc_freq.get(token, 0)
                if df > 0:
                    idf = 1.0 + (self.doc_count / df)
                else:
                    idf = 1.0
                
                # Score documents
                for doc_id, positions in self.index[token].items():
                    tf = len(positions)
                    doc_scores[doc_id] += tf * idf
        
        # Sort by score
        ranked_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Return documents
        return [self.documents[doc_id] for doc_id, _ in ranked_docs]
    
    async def get_document(self, doc_id: str) -> Optional[IndexedDocument]:
        """Get document by ID"""
        # Check cache first
        cache_key = f"index:doc:{doc_id}"
        cached = await cache_service.get(cache_key)
        if cached:
            return IndexedDocument(**cached)
        
        return self.documents.get(doc_id)
    
    def get_term_stats(self, term: str) -> dict:
        """Get statistics for a term"""
        term = term.lower()
        
        return {
            "term": term,
            "document_frequency": self.doc_freq.get(term, 0),
            "documents": len(self.index.get(term, {})),
            "total_occurrences": sum(
                len(positions)
                for positions in self.index.get(term, {}).values()
            ),
        }
    
    async def delete_document(self, doc_id: str):
        """Remove document from index"""
        if doc_id not in self.documents:
            return
        
        # Get document
        doc = self.documents[doc_id]
        
        # Tokenize to find terms
        text = f"{doc.title} {doc.content}"
        tokens = set(self.tokenizer.tokenize(text))
        
        # Remove from inverted index
        for token in tokens:
            if doc_id in self.index[token]:
                del self.index[token][doc_id]
                self.doc_freq[token] -= 1
                
                # Clean up empty entries
                if not self.index[token]:
                    del self.index[token]
                    del self.doc_freq[token]
        
        # Remove document
        del self.documents[doc_id]
        self.doc_count -= 1
        
        # Remove from cache
        cache_key = f"index:doc:{doc_id}"
        await cache_service.delete(cache_key)
    
    def get_stats(self) -> dict:
        """Get index statistics"""
        return {
            "total_documents": self.doc_count,
            "total_terms": len(self.index),
            "avg_doc_length": sum(
                len(f"{doc.title} {doc.content}".split())
                for doc in self.documents.values()
            ) / self.doc_count if self.doc_count > 0 else 0,
        }


class IndexManager:
    """Manages multiple indices and provides unified search"""
    
    def __init__(self):
        self.indices = {}  # index_name -> InvertedIndex
        self.default_index = "main"
    
    def get_index(self, name: str = None) -> InvertedIndex:
        """Get or create index"""
        name = name or self.default_index
        
        if name not in self.indices:
            self.indices[name] = InvertedIndex()
        
        return self.indices[name]
    
    async def index_web_result(
        self,
        result: dict,
        index_name: str = None,
    ):
        """Index a web search result"""
        index = self.get_index(index_name)
        
        # Create document ID from URL
        doc_id = hashlib.md5(result.get('url', '').encode()).hexdigest()
        
        # Create indexed document
        doc = IndexedDocument(
            doc_id=doc_id,
            title=result.get('title', ''),
            content=result.get('snippet', ''),
            url=result.get('url', ''),
            source=result.get('source', ''),
            indexed_at=datetime.utcnow(),
            metadata=result.get('metadata', {}),
        )
        
        await index.add_document(doc)
    
    async def index_batch(
        self,
        results: list[dict],
        index_name: str = None,
    ):
        """Index multiple results"""
        tasks = [
            self.index_web_result(result, index_name)
            for result in results
        ]
        await asyncio.gather(*tasks)
    
    async def search_all(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search across all indices"""
        all_results = []
        
        for index_name, index in self.indices.items():
            results = await index.search(query, limit)
            for doc in results:
                result_dict = doc.to_dict()
                result_dict['index'] = index_name
                all_results.append(result_dict)
        
        return all_results[:limit]
    
    def get_all_stats(self) -> dict:
        """Get statistics for all indices"""
        return {
            index_name: index.get_stats()
            for index_name, index in self.indices.items()
        }


class SearchIndexOptimizer:
    """Optimize search index performance"""
    
    def __init__(self, index: InvertedIndex):
        self.index = index
    
    async def optimize(self):
        """Optimize index structure"""
        logger.info("Optimizing search index...")
        
        # 1. Remove rare terms (appear in < 2 documents)
        rare_terms = [
            term for term, freq in self.index.doc_freq.items()
            if freq < 2
        ]
        
        for term in rare_terms:
            if term in self.index.index:
                del self.index.index[term]
            if term in self.index.doc_freq:
                del self.index.doc_freq[term]
        
        logger.info(f"Removed {len(rare_terms)} rare terms")
        
        # 2. Compress position arrays (keep only count, not positions)
        for term_docs in self.index.index.values():
            for doc_id in term_docs:
                positions = term_docs[doc_id]
                if len(positions) > 10:
                    # Keep only count for high-frequency terms
                    term_docs[doc_id] = [len(positions)]
        
        logger.info("Index optimization complete")
    
    async def rebuild(self):
        """Rebuild index from documents"""
        logger.info("Rebuilding search index...")
        
        # Save documents
        documents = list(self.index.documents.values())
        
        # Clear index
        self.index.index.clear()
        self.index.doc_freq.clear()
        self.index.documents.clear()
        self.index.doc_count = 0
        
        # Re-add documents
        for doc in documents:
            await self.index.add_document(doc)
        
        logger.info(f"Rebuilt index with {len(documents)} documents")


# Global index manager
index_manager = IndexManager()
