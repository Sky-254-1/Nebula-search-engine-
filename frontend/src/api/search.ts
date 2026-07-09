import { apiClient } from './client';
import { 
  SearchResult, 
  IntelligentSearchResponse,
  SuggestionsResponse,
  AutocompleteResponse,
  SpellCheckResponse,
  TrendingResponse,
  PopularResponse,
  SearchProfile,
  SearchHistoryItem 
} from '@/types';

export interface SearchParams {
  q: string;
  backends?: string;
  page?: number;
  page_size?: number;
  enable_semantic?: boolean;
  enable_personalization?: boolean;
  enable_spell_check?: boolean;
  enable_diversity?: boolean;
}

export interface LegacySearchParams {
  q: string;
  backend?: string;
}

export const searchApi = {
  // Main intelligent search (v2)
  async search(params: SearchParams): Promise<IntelligentSearchResponse> {
    return apiClient.get<IntelligentSearchResponse>('/v2/search', params);
  },

  // Semantic search
  async semanticSearch(q: string, topK: number = 10, threshold: number = 0.5): Promise<IntelligentSearchResponse> {
    return apiClient.get<IntelligentSearchResponse>('/v2/search/semantic', { q, top_k: topK, threshold });
  },

  // Suggestions and autocomplete
  async getSuggestions(q: string, limit: number = 10): Promise<SuggestionsResponse> {
    return apiClient.get<SuggestionsResponse>('/v2/search/suggest', { q, limit });
  },

  async autocomplete(q: string, limit: number = 10): Promise<AutocompleteResponse> {
    return apiClient.get<AutocompleteResponse>('/v2/search/autocomplete', { q, limit });
  },

  async spellCheck(q: string): Promise<SpellCheckResponse> {
    return apiClient.get<SpellCheckResponse>('/v2/search/spell-check', { q });
  },

  // Trending and popular
  async getTrending(limit: number = 10, hours: number = 24): Promise<TrendingResponse> {
    return apiClient.get<TrendingResponse>('/v2/search/trending', { limit, hours });
  },

  async getPopular(limit: number = 10): Promise<PopularResponse> {
    return apiClient.get<PopularResponse>('/v2/search/popular', { limit });
  },

  // Click tracking
  async logClick(query: string, position: number, url: string, sessionId?: string): Promise<void> {
    await apiClient.post('/v2/search/click', { query, position, url, session_id: sessionId });
  },

  // User search profile
  async getProfile(): Promise<SearchProfile> {
    return apiClient.get<SearchProfile>('/v2/search/profile');
  },

  // Search analytics
  async getAnalytics(query?: string): Promise<any> {
    return apiClient.get('/v2/search/analytics', { query });
  },

  // Legacy search (kept for backward compatibility)
  async webSearch(params: LegacySearchParams): Promise<SearchResult[]> {
    return apiClient.get<SearchResult[]>('/search/web', params);
  },

  async orchestratedSearch(params: SearchParams): Promise<any> {
    return apiClient.get('/search/orchestrate', params);
  },

  async getSearchHistory(limit: number = 20): Promise<{ history: SearchHistoryItem[] }> {
    return apiClient.get('/search/history', { limit });
  }
};
