"""Metadata synchronization for incremental re-indexing."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.incremental.config import (
    IncrementalConfig,
    get_incremental_config,
)

logger = logging.getLogger("nebula.incremental.metadata")


@dataclass
class MetadataSyncResult:
    """Result of metadata synchronization."""
    document_id: int
    fields_updated: List[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


class MetadataSynchronizer:
    """
    Synchronizes document metadata without regenerating embeddings.
    
    Only updates searchable metadata fields that affect search results.
    """

    def __init__(self, config: Optional[IncrementalConfig] = None):
        """Initialize metadata synchronizer."""
        self._config = config or get_incremental_config()
    
    async def sync_metadata(
        self,
        db_session,
        document_id: int,
        old_metadata: Dict[str, Any],
        new_metadata: Dict[str, Any],
        fields_to_sync: Optional[List[str]] = None,
    ) -> MetadataSyncResult:
        """
        Synchronize metadata changes.
        
        Args:
            db_session: Database session
            document_id: Document identifier
            old_metadata: Previous metadata
            new_metadata: New metadata
            fields_to_sync: Specific fields to sync (None for all tracked)
            
        Returns:
            MetadataSyncResult
        """
        if not fields_to_sync:
            fields_to_sync = self._config.metadata_fields_to_track
        
        result = MetadataSyncResult(document_id=document_id)
        
        try:
            # Compute changes
            changes = {}
            for field in fields_to_sync:
                old_value = old_metadata.get(field)
                new_value = new_metadata.get(field)
                
                if old_value != new_value:
                    changes[field] = new_value
            
            if not changes:
                result.success = True
                logger.info("No metadata changes for document %d", document_id)
                return result
            
            # Update database
            await self._update_database(
                db_session, document_id, changes, new_metadata
            )
            
            # Update search index (if needed)
            await self._update_search_index(db_session, document_id, changes)
            
            # Update vector store metadata (if applicable)
            await self._update_vector_metadata(db_session, document_id, changes)
            
            result.fields_updated = list(changes.keys())
            result.success = True
            
            logger.info(
                "Synchronized metadata for document %d: %s",
                document_id, ", ".join(result.fields_updated)
            )
            
            return result
            
        except Exception as exc:
            logger.error("Metadata sync failed for document %d: %s", document_id, exc)
            result.error = str(exc)
            return result
    
    async def _update_database(
        self,
        db_session,
        document_id: int,
        changes: Dict[str, Any],
        new_metadata: Dict[str, Any],
    ) -> None:
        """
        Update database with new metadata.
        
        Args:
            db_session: Database session
            document_id: Document identifier
            changes: Changed fields
            new_metadata: Complete new metadata
        """
        # Update metadata column
        metadata_json = json.dumps(new_metadata, default=str)
        
        await db_session.execute(
            "UPDATE documents SET metadata = ? WHERE id = ?",
            (metadata_json, document_id),
        )
        await db_session.commit()
        
        logger.debug("Updated metadata in database for document %d", document_id)
    
    async def _update_search_index(
        self,
        db_session,
        document_id: int,
        changes: Dict[str, Any],
    ) -> None:
        """
        Update search index with new metadata.
        
        Args:
            db_session: Database session
            document_id: Document identifier
            changes: Changed fields
        """
        # Fields that affect search
        searchable_fields = [
            "title", "description", "author", "category",
            "tags", "language"
        ]
        
        relevant_changes = {k: v for k, v in changes.items() if k in searchable_fields}
        
        if relevant_changes:
            # Update search index (placeholder - would update actual search index)
            logger.debug(
                "Would update search index for document %d with changes: %s",
                document_id, relevant_changes
            )
    
    async def _update_vector_metadata(
        self,
        db_session,
        document_id: int,
        changes: Dict[str, Any],
    ) -> None:
        """
        Update vector store metadata.
        
        Args:
            db_session: Database session
            document_id: Document identifier
            changes: Changed fields
        """
        # Get all chunk embedding IDs
        cursor = await db_session.execute(
            "SELECT chunk_id, embedding_id FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )
        rows = await cursor.fetchall()
        
        updated = 0
        for chunk_id, embedding_id in rows:
            if embedding_id:
                # Update vector metadata (placeholder)
                logger.debug(
                    "Would update metadata for vector %s (document %d chunk %d)",
                    embedding_id, document_id, chunk_id
                )
                updated += 1
        
        if updated > 0:
            logger.debug(
                "Updated metadata for %d vectors for document %d",
                updated, document_id
            )


class MetadataTracker:
    """Tracks metadata changes over time."""

    def __init__(self) -> None:
        """Initialize metadata tracker."""
        self._history: Dict[int, List[Dict[str, Any]]] = {}
    
    def record_change(
        self,
        document_id: int,
        field: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """
        Record a metadata change.
        
        Args:
            document_id: Document identifier
            field: Field that changed
            old_value: Previous value
            new_value: New value
        """
        if document_id not in self._history:
            self._history[document_id] = []
        
        self._history[document_id].append({
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
    
    def get_history(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get metadata change history for document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of metadata changes
        """
        return self._history.get(document_id, [])
    
    def clear_history(self, document_id: int) -> None:
        """
        Clear history for document.
        
        Args:
            document_id: Document identifier
        """
        if document_id in self._history:
            del self._history[document_id]


class MetadataVersioning:
    """Manages metadata versioning."""

    def __init__(self) -> None:
        """Initialize metadata versioning."""
        self._versions: Dict[int, Dict[str, Any]] = {}
        self._counters: Dict[str, int] = {}
    
    def create_version(
        self,
        document_id: int,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Create a new version of metadata.
        
        Args:
            document_id: Document identifier
            metadata: Metadata to version
            
        Returns:
            Version identifier
        """
        # Increment counter
        key = f"doc_{document_id}"
        self._counters[key] = self._counters.get(key, 0) + 1
        version = f"{document_id}_v{self._counters[key]}"
        
        # Store version
        self._versions[version] = metadata.copy()
        
        logger.debug("Created metadata version %s for document %d", version, document_id)
        return version
    
    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata by version.
        
        Args:
            version_id: Version identifier
            
        Returns:
            Metadata dict or None
        """
        return self._versions.get(version_id)
    
    def update_version(self, version_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update existing version.
        
        Args:
            version_id: Version identifier
            metadata: New metadata
            
        Returns:
            True if updated
        """
        if version_id in self._versions:
            self._versions[version_id] = metadata
            return True
        return False