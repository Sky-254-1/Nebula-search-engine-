# API Documentation — v1.1

Base URL: `http://localhost:8000` (development)

All authenticated endpoints require: `Authorization: Bearer <access_token>`

## Existing endpoints (preserved)

See README and `/docs` for auth, search, AI, and storage routes.

## Vector indexing (v1.1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/vector/documents/{id}/status` | Indexing status for a document |
| POST | `/api/v1/vector/documents/{id}/reindex` | Queue document reindex |
| POST | `/api/v1/vector/documents/{id}/index-now` | Synchronous index (small docs) |
| POST | `/api/v1/vector/documents/reindex-all` | Queue all user documents |
| POST | `/api/v1/vector/search` | Hybrid vector + keyword search |
| GET | `/api/v1/vector/citations` | Recent citation log |
| GET | `/api/v1/vector/stats` | Chunk and document counts |
| POST | `/api/v1/vector/export` | Export vector chunks JSON |

### Vector search request

```json
{
  "query": "hybrid search example",
  "top_k": 10
}
```

### Vector search response

```json
{
  "query": "hybrid search example",
  "total": 3,
  "results": [
    {
      "document_id": 1,
      "chunk_id": 2,
      "filename": "notes.txt",
      "content": "...",
      "score": 0.82,
      "vector_score": 0.75,
      "keyword_score": 1.0
    }
  ]
}
```

### Document index status

```json
{
  "id": 1,
  "filename": "notes.txt",
  "status": "indexed",
  "indexed_at": "2026-06-25T12:00:00+00:00",
  "error_message": null
}
```

Status values: `pending`, `indexing`, `indexed`, `duplicate`, `error`

## Supported upload formats (extended)

`.txt`, `.md`, `.json`, `.csv`, `.pdf`, `.html`, `.htm`, `.docx`
