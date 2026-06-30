export const config = {
  apiBase: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
  syncQueueKey: 'nebula_sync_queue',
  searchCacheKey: 'nebula_search_cache',
  offlineMode: false,
  maxCacheAge: 1000 * 60 * 60 * 24,
  searchDebounceMs: 300,
  startupTimeoutMs: 2000,
};
export const isNative = !!(window as any).Capacitor?.isNative;
