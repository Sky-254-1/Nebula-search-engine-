import { apiClient } from './client';
import { AIResponse, ChatMessage, ChatHistoryResponse, SynthesizeRequest, SynthesizeResponse } from '@/types';

export const aiApi = {
  async ask(prompt: string): Promise<AIResponse> {
    return apiClient.post<AIResponse>('/ai/ask', { prompt });
  },

  async askStream(prompt: string, onChunk: (chunk: string) => void): Promise<void> {
    const baseURL = apiClient['client'].defaults.baseURL || '/api/v1';
    const response = await fetch(`${baseURL}/ai/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      throw new Error('Stream request failed');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            return;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            }
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  },

  async getChatHistory(): Promise<ChatHistoryResponse> {
    return apiClient.get<ChatHistoryResponse>('/ai/chat/history');
  },

  async clearChatHistory(): Promise<void> {
    await apiClient.delete('/ai/chat/history');
  },

  async synthesize(query: string, snippets: string[]): Promise<SynthesizeResponse> {
    return apiClient.post<SynthesizeResponse>('/ai/synthesize', { query, snippets });
  }
};
