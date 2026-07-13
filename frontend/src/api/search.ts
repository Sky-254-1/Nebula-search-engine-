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
  // Main unified search endpoint
  async search(params: SearchParams): Promise<any> {
    return apiClient.post('/search_v2/', {
      q: params.q,
      page: params.page || 1,
      page_size: params.page_size || 20,
      enable_semantic: params.enable_semantic ?? true,
      enable_personalization: params.enable_personalization ?? true,
      enable_spell_check: params.enable_spell_check ?? true,
      enable_diversity: params.enable_diversity ?? true,
    });
  },

  // Suggestions and autocomplete
  async getSuggestions(q: string, limit: number = 10): Promise<SuggestionsResponse> {
    return apiClient.get<SuggestionsResponse>('/search/suggestions', { q, limit });
  },

  async autocomplete(q: string, limit: number = 10): Promise<AutocompleteResponse> {
    return apiClient.get<AutocompleteResponse>('/search/autocomplete', { q, limit });
  },

  async spellCheck(q: string): Promise<SpellCheckResponse> {
    // Backend doesn't have separate spell check endpoint, it's part of search
    return { original: q, corrected: q, was_corrected: false };
  },

  // Trending and popular
  async getTrending(limit: number = 10, hours: number = 24): Promise<TrendingResponse> {
    // Not implemented in current backend
    return { trending: [], period_hours: hours };
  },

  async getPopular(limit: number = 10): Promise<PopularResponse> {
    // Not implemented in current backend
    return { popular: [] };
  },

  // Search history
  async getSearchHistory(limit: number = 20): Promise<{ history: SearchHistoryItem[] }> {
    return apiClient.get('/search_v2/history', { limit });
  },

  // Save/search management
  async saveSearch(query: string, mode: string = 'hybrid', filters?: Record<string, any>): Promise<any> {
    return apiClient.post('/search_v2/save', { query, mode, filters });
  },

  async getSavedSearches(): Promise<any> {
    return apiClient.get('/search_v2/saved');
  },

  async deleteSavedSearch(searchId: number): Promise<void> {
    await apiClient.delete(`/search_v2/saved/${searchId}`);
  },

  // Legacy web search
  async webSearch(params: LegacySearchParams): Promise<SearchResult[]> {
    try {
      const response = await apiClient.get<{ results?: SearchResult[] }>('/search/web', { q: params.q, backend: params.backend });
      return response.results || [];
    } catch {
      return [];
    }
  },

  // Clear history
  async clearHistory(): Promise<void> {
    await apiClient.delete('/search_v2/history');
  }
};
