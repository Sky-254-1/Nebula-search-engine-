import { Preferences } from '@capacitor/preferences';
import { config, isNative } from './config';
import { enqueueJob } from '../sync/queue';

interface SearchResult {
  title: string;
  snippet: string;
  url: string;
  source: string;
}

interface CachedSearch {
  query: string;
  results: SearchResult[];
  timestamp: number;
}

export async function searchOfflineFirst(
  query: string,
  token: string,
  backend = 'wikipedia'
): Promise<SearchResult[]> {
  const cacheKey = `${config.searchCacheKey}:${query}:${backend}`;
  const { value } = await Preferences.get({ key: cacheKey });
  const cached: CachedSearch | null = value ? JSON.parse(value) : null;

  if (cached && Date.now() - cached.timestamp < config.maxCacheAge) {
    return cached.results;
  }

  try {
    const res = await fetch(
      `${config.apiBase}/api/v1/search/web?q=${encodeURIComponent(query)}&backend=${backend}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!res.ok) throw new Error(`Search failed: ${res.status}`);
    const results: SearchResult[] = await res.json();
    await Preferences.set({
      key: cacheKey,
      value: JSON.stringify({ query, results, timestamp: Date.now() }),
    });
    return results;
  } catch (err) {
    if (cached) {
      console.warn('[Nebula Mobile] Network unavailable, using stale cache');
      return cached.results;
    }
    throw err;
  }
}

export async function searchVoice(
  query: string,
  token: string
): Promise<SearchResult[]> {
  try {
    const { SpeechRecognition } = await import('@capacitor-community/speech-recognition');
    const result = await SpeechRecognition.start({ language: 'en-US', maxResults: 1 });
    const transcript = result.matches?.[0]?.[0] || query;
    return searchOfflineFirst(transcript, token);
  } catch {
    return searchOfflineFirst(query, token);
  }
}

export async function saveSearchOffline(query: string, results: SearchResult[]) {
  await enqueueJob({
    id: crypto.randomUUID(),
    type: 'search',
    payload: { q: query, results: JSON.stringify(results) },
  });
}
