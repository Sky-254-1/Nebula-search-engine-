```js
import { useCallback, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

function escapeHtml(value = '') {
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}

export function useSearch() {
  const { api, isAuthenticated } = useAuth();

  const [results, setResults] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(
    async (
      query,
      {
        backends = 'wikipedia',
        page = 1,
        page_size = 10,
      } = {}
    ) => {
      if (!query?.trim()) return;

      setLoading(true);
      setError(null);

      try {
        if (isAuthenticated) {
          const data = await api.searchOrchestrate({
            q: query,
            backends,
            page,
            page_size,
          });

          setResults(data.results || []);
          setMeta(data);
        } else {
          const offset = (page - 1) * page_size;

          const url =
            `https://en.wikipedia.org/w/api.php` +
            `?action=query` +
            `&list=search` +
            `&srsearch=${encodeURIComponent(query)}` +
            `&format=json` +
            `&origin=*` +
            `&srlimit=${page_size}` +
            `&sroffset=${offset}`;

          const res = await fetch(url);

          if (!res.ok) {
            throw new Error('Search request failed');
          }

          const json = await res.json();

          const mapped = (json.query?.search || []).map((item) => ({
            title: item.title || '',

            // Safe output encoding
            snippet: escapeHtml(item.snippet || ''),

            url:
              `https://en.wikipedia.org/wiki/${encodeURIComponent(
                (item.title || '').replace(/ /g, '_')
              )}`,

            source: 'wikipedia',
          }));

          setResults(mapped);

          setMeta({
            query,
            total:
              json.query?.searchinfo?.totalhits ??
              mapped.length,
            page,
            page_size,
            cached: false,
          });
        }
      } catch (err) {
        setError(err?.message || 'Search failed');
        setResults([]);
        setMeta(null);
      } finally {
        setLoading(false);
      }
    },
    [api, isAuthenticated]
  );

  return {
    results,
    meta,
    loading,
    error,
    search,
  };
}
```
