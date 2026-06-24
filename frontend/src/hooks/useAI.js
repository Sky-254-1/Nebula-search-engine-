import { useCallback, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

export function useAI() {
  const { api, isAuthenticated } = useAuth();
  const [answer, setAnswer] = useState(null);
  const [provider, setProvider] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const ask = useCallback(
    async (prompt) => {
      if (!prompt.trim()) return;
      setLoading(true);
      setError(null);
      try {
        if (isAuthenticated) {
          const data = await api.aiAsk(prompt);
          setAnswer(data.answer);
          setProvider(data.provider);
        } else {
          const res = await fetch(
            `https://api.duckduckgo.com/?q=${encodeURIComponent(prompt)}&format=json&no_redirect=1&t=Nebula`
          );
          const json = await res.json();
          setAnswer(json.AbstractText || json.Answer || null);
          setProvider('duckduckgo');
        }
      } catch (err) {
        setError(err.message || 'AI request failed');
        setAnswer(null);
      } finally {
        setLoading(false);
      }
    },
    [api, isAuthenticated]
  );

  return { answer, provider, loading, error, ask };
}
