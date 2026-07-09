import { apiClient } from './client';
import { SearchResult, OrchestratedSearchResponse, SearchHistoryItem } from '@/types';

export interface SearchParams {
  q: string;
  backend?: string;
  page?: number;
  page_size?: number;
  backends?: string;
}

export interface OrchestrateParams {
  q: string;
  backends?: string;
  page?: number;
  page_size?: number;
}

export const searchApi = {
  async webSearch(params: SearchParams): Promise<SearchResult[]> {
    return apiClient.get<SearchResult[]>('/search/web', params);
  }

  async orchestratedSearch(params: OrchestrateParams): Promise<OrchestratedSearchResponse> {
    return apiClient.get<OrchestratedSearchResponse>('/search/orchestrate', params);
  }

  async getSearchHistory(limit: number = 20): Promise<{ history: SearchHistoryItem[] }> {
    return apiClient.get('/search/history', { limit });
  }
};