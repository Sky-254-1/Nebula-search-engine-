import { useCallback, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { loadHistory, saveHistory } from '../utils/storage';

export function useSearch() {
  const { api, isAuthenticated } = useAuth();
  const [results, setResults] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(
    async (query, { backends = 'wikipedia', page = 1, page_size = 10 } = {}) => {
      if (!query.trim()) return;
      setLoading(true);
      setError(null);
      try {
        if (isAuthenticated) {
          const data = await api.searchOrchestrate({ q: query, backends, page, page_size });
          setResults(data.results || []);
          setMeta(data);
        } else {
          const url = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&format=json&origin=*&srlimit=${page_size}`;
          const res = await fetch(url);
          const json = await res.json();
          const mapped = (json.query?.search || []).map((item) => ({
            title: item.title,
            snippet: item.snippet?.replace(/<[^>]+>/g, '') || '',
            url: `https://en.wikipedia.org/wiki/${encodeURIComponent(item.title.replace(/ /g, '_'))}`,
            source: 'wikipedia',
          }));
          setResults(mapped);
          setMeta({ query, total: mapped.length, page, page_size, cached: false });
        }
        const hist = [query, ...loadHistory().filter((h) => h !== query)].slice(0, 8);
        saveHistory(hist);
      } catch (err) {
        setError(err.message || 'Search failed');
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [api, isAuthenticated]
  );

  return { results, meta, loading, error, search };
}
