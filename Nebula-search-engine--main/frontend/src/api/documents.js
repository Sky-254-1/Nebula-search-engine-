export function createDocumentApi(authedFetch) {
  return {
    listDocuments: () => authedFetch('/storage/documents'),
    uploadDocument: (file) => {
      const form = new FormData();
      form.append('file', file);
      return authedFetch('/storage/documents', {
        method: 'POST',
        body: form,
        headers: {},
      });
    },
    deleteDocument: (docId) =>
      authedFetch(`/storage/documents/${docId}`, { method: 'DELETE' }),
    documentStatus: (docId) => authedFetch(`/vector/documents/${docId}/status`),
    reindexDocument: (docId) =>
      authedFetch(`/vector/documents/${docId}/reindex`, { method: 'POST' }),
    vectorSearch: (query, topK = 10) =>
      authedFetch('/vector/search', {
        method: 'POST',
        body: JSON.stringify({ query, top_k: topK }),
      }),
    vectorStats: () => authedFetch('/vector/stats'),
    listCitations: () => authedFetch('/vector/citations'),
  };
}
