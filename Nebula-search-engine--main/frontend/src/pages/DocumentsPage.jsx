import { useEffect, useState, useRef } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';

export function DocumentsPage() {
  const { t } = useTranslation();
  const { api } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    setLoading(true);
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents || []);
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(file);
      toast.success('Document uploaded');
      loadDocuments();
    } catch (err) {
      toast.error(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function handleDelete(docId) {
    try {
      await api.deleteDocument(docId);
      toast.success('Document deleted');
      loadDocuments();
    } catch {
      toast.error('Delete failed');
    }
  }

  async function handleReindex(docId) {
    try {
      await api.reindexDocument(docId);
      toast.success('Reindex queued');
    } catch {
      toast.error('Reindex failed');
    }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const data = await api.vectorSearch(searchQuery);
      setSearchResults(data);
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="documents-page">
      <h1>Documents</h1>

      <section className="documents-upload">
        <h2>Upload Document</h2>
        <input
          type="file"
          ref={fileRef}
          onChange={handleUpload}
          accept=".txt,.md,.pdf,.docx,.html,.htm,.json,.csv"
          disabled={uploading}
        />
        {uploading && <p>Uploading…</p>}
      </section>

      <section className="documents-search">
        <h2>Vector Search</h2>
        <form onSubmit={handleSearch} className="flex-row">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search your documents…"
          />
          <button type="submit" className="btn primary" disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {searchResults && (
          <div className="search-results">
            <p>{searchResults.total} result(s)</p>
            {searchResults.results.map((r, i) => (
              <div key={i} className="result-card">
                <p className="result-filename">{r.filename}</p>
                <p className="result-content">{r.content}</p>
                <p className="result-score">Score: {r.score.toFixed(3)}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="documents-list">
        <h2>My Documents ({documents.length})</h2>
        {loading ? (
          <p>Loading…</p>
        ) : documents.length === 0 ? (
          <p>No documents uploaded yet</p>
        ) : (
          <table className="documents-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.filename}</td>
                  <td>{doc.content_type || '-'}</td>
                  <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '-'}</td>
                  <td className="actions-cell">
                    <button className="btn btn-sm" onClick={() => handleReindex(doc.id)}>Reindex</button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(doc.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
