import { apiClient } from './client';
import { AIRequest, AIResponse, ChatMessage, SynthesizeRequest } from '@/types';

export interface AskAIParams {
  prompt: string;
}

export interface StreamAIParams {
  prompt: string;
  onChunk: (chunk: string) => void;
  onComplete: () => void;
  onError: (error: Error) => void;
}

export const aiApi = {
  async ask(params: AskAIParams): Promise<AIResponse> {
    return apiClient.post<AIResponse>('/ai/ask', params);
  }

  async askStream(params: StreamAIParams): Promise<void> {
    const { prompt, onChunk, onComplete, onError } = params;
    
    try {
      const response = await fetch(`${API_BASE_URL}/ai/ask/stream`, {
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
              onComplete();
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                onChunk(parsed.chunk);
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      onComplete();
    } catch (error) {
      onError(error instanceof Error ? error : new Error('Unknown error'));
    }
  },

  async getChatHistory(): Promise<{ messages: ChatMessage[] }> {
    return apiClient.get('/ai/chat/history');
  },

  async clearChatHistory(): Promise<void> {
    return apiClient.post('/ai/chat/history/clear');
  },

  async synthesize(params: SynthesizeRequest): Promise<{ synthesis: string; sources: string[] }> {
    return apiClient.post('/ai/synthesize', params);
  }
};