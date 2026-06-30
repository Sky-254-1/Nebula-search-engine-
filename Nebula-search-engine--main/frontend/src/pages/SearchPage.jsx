import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { SearchBar } from '../components/SearchBar';
import { ResultsList } from '../components/ResultsList';
import { Pagination } from '../components/Pagination';
import { ChatPanel } from '../components/ChatPanel';
import { useSearch } from '../hooks/useSearch';
import { useAI } from '../hooks/useAI';
import { useChat } from '../hooks/useChat';
import { useSearchState } from '../state/SearchContext';

export default function SearchPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { query, setQuery, page, setPage, config } = useSearchState();
  const { results, meta, loading, error, search } = useSearch();
  const { answer, provider, loading: aiLoading, streaming, error: aiError, ask } = useAI();
  const { messages, loading: chatLoading, clear: clearChat, reload: reloadChat } = useChat();

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) {
      setQuery(q);
      runSearch(q, 1);
    }
  }, []);

  async function runSearch(q = query, targetPage = page) {
    const trimmed = (q || query).trim();
    if (!trimmed) return;
    setQuery(trimmed);
    setSearchParams({ q: trimmed });
    await search(trimmed, {
      backends: config.backends,
      page: targetPage,
      page_size: config.pageSize || 10,
    });
    await ask(trimmed);
    reloadChat();
  }

  function handlePageChange(nextPage) {
    setPage(nextPage);
    runSearch(query, nextPage);
  }

  return (
    <div className="search-page">
      <div className="search-page-bar">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={() => { setPage(1); runSearch(query, 1); }}
          loading={loading}
        />
      </div>

      {(error || aiError) && (
        <div className="error-box">
          <p>{error || aiError}</p>
          <button type="button" className="btn btn-ghost" onClick={() => runSearch()}>{t('common.retry')}</button>
        </div>
      )}

      {(answer || aiLoading) && (
        <section className="ai-box">
          <h2>{t('search.aiOverview')} {provider ? `· ${provider}` : ''} {streaming && <span className="streaming-dot" />}</h2>
          {aiLoading && !answer ? (
            <div className="ai-skeleton">
              <div className="skeleton-line" />
              <div className="skeleton-line short" />
            </div>
          ) : (
            <p>{answer}</p>
          )}
        </section>
      )}

      <div className="search-page-content">
        <div className="search-page-results">
          {meta && (
            <p className="results-meta">
              {t('search.resultsCount', { count: meta.total, query: meta.query })}
              {meta.cached ? ` ${t('search.cached')}` : ''}
            </p>
          )}
          <ResultsList results={results} loading={loading} query={meta?.query || query} />
          <Pagination
            page={meta?.page || page}
            pageSize={meta?.page_size || config.pageSize || 10}
            total={meta?.total || 0}
            onPageChange={handlePageChange}
            disabled={loading}
          />
        </div>

        <aside className="search-page-sidebar">
          <ChatPanel messages={messages} loading={chatLoading} onClear={clearChat} />
        </aside>
      </div>
    </div>
  );
}
