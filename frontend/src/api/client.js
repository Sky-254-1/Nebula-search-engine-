const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function buildClient(getTokens, setTokens, clearTokens) {
  async function authedFetch(path, options = {}) {
    const tokens = getTokens();
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
    if (tokens?.access_token) {
      headers.Authorization = `Bearer ${tokens.access_token}`;
    }

    let response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (response.status === 401 && tokens?.refresh_token) {
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });
      if (refreshRes.ok) {
        const refreshed = await refreshRes.json();
        setTokens(refreshed);
        headers.Authorization = `Bearer ${refreshed.access_token}`;
        response = await fetch(`${API_BASE}${path}`, { ...options, headers });
      }
    }

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(String(detail), response.status);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  return {
    signup: (email, password) =>
      authedFetch('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) }),
    login: async (email, password) => {
      const data = await authedFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setTokens(data);
      return data;
    },
    logout: async () => {
      const tokens = getTokens();
      if (tokens?.refresh_token) {
        await authedFetch('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: tokens.refresh_token }),
        }).catch(() => null);
      }
      clearTokens();
    },
    me: () => authedFetch('/auth/me'),
    searchOrchestrate: ({ q, backends = 'wikipedia', page = 1, page_size = 10 }) =>
      authedFetch(
        `/search/orchestrate?q=${encodeURIComponent(q)}&backends=${encodeURIComponent(backends)}&page=${page}&page_size=${page_size}`
      ),
    searchHistory: () => authedFetch('/search/history'),
    aiAsk: (prompt) =>
      authedFetch('/ai/ask', { method: 'POST', body: JSON.stringify({ prompt }) }),
    aiSynthesize: (query, snippets) =>
      authedFetch('/ai/synthesize', {
        method: 'POST',
        body: JSON.stringify({ query, snippets }),
      }),
    chatHistory: () => authedFetch('/ai/chat/history'),
    clearChat: () => authedFetch('/ai/chat/history', { method: 'DELETE' }),
    health: () => fetch('/health').then((r) => r.json()),
  };
}
