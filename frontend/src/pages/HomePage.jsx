import { useState } from 'react';
import { AuthModal } from '../components/AuthModal';
import { Header } from '../components/Header';
import { ResultsList } from '../components/ResultsList';
import { SearchBar } from '../components/SearchBar';
import { Toast } from '../components/Toast';
import { useAI } from '../hooks/useAI';
import { useSearch } from '../hooks/useSearch';
import { loadConfig, saveConfig } from '../utils/storage';

export function HomePage() {
  const [query, setQuery] = useState('');
  const [authOpen, setAuthOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [config, setConfig] = useState(() => loadConfig({ theme: 'dark', backends: 'wikipedia' }));
  const { results, meta, loading, error, search } = useSearch();
  const { answer, provider, loading: aiLoading, error: aiError, ask } = useAI();

  function toggleTheme() {
    const theme = config.theme === 'dark' ? 'light' : 'dark';
    const next = { ...config, theme };
    setConfig(next);
    saveConfig(next);
    document.body.dataset.theme = theme;
  }

  async function runSearch(q = query) {
    await search(q, { backends: config.backends });
    await ask(q);
    if (error) setToast({ message: error, type: 'error' });
  }

  return (
    <div className="page">
      <Header onAuthClick={() => setAuthOpen(true)} theme={config.theme} onToggleTheme={toggleTheme} />
      <main className="hero">
        <h1 className="hero-title">Nebula Search</h1>
        <p className="hero-tagline">Private · Intelligent · Hybrid search</p>
        <SearchBar value={query} onChange={setQuery} onSubmit={runSearch} loading={loading} />
        <div className="backend-select">
          <label>
            Backends
            <select
              value={config.backends}
              onChange={(e) => {
                const next = { ...config, backends: e.target.value };
                setConfig(next);
                saveConfig(next);
              }}
            >
              <option value="wikipedia">Wikipedia</option>
              <option value="wikipedia,brave">Wikipedia + Brave</option>
              <option value="wikipedia,serpapi">Wikipedia + SerpAPI</option>
            </select>
          </label>
        </div>
        {(error || aiError) && (
          <div className="error-box">
            <p>{error || aiError}</p>
            <button type="button" className="btn ghost" onClick={() => runSearch()}>
              Retry
            </button>
          </div>
        )}
        {(answer || aiLoading) && (
          <section className="ai-box">
            <h2>AI Overview {provider ? `· ${provider}` : ''}</h2>
            {aiLoading ? <p className="muted">Generating answer…</p> : <p>{answer}</p>}
          </section>
        )}
        {meta && (
          <section className="results-section">
            <p className="results-meta">
              {meta.total} results for “{meta.query}” {meta.cached ? '(cached)' : ''}
            </p>
            <ResultsList results={results} loading={loading} query={meta.query} />
          </section>
        )}
      </main>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
      <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />
    </div>
  );
}
