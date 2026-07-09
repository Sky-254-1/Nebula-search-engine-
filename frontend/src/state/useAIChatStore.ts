import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { ChatMessage } from '@/types';
import { aiApi } from '@/api/ai';

interface AIChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  currentStreamMessage: string;
  error: string | null;
}

interface AIChatActions {
  sendMessage: (prompt: string) => Promise<void>;
  sendMessageStream: (prompt: string) => Promise<void>;
  fetchChatHistory: () => Promise<void>;
  clearChatHistory: () => Promise<void>;
  clearError: () => void;
  setStreaming: (streaming: boolean) => void;
}

type AIChatStore = AIChatState & AIChatActions;

export const useAIChatStore = create<AIChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      isStreaming: false,
      currentStreamMessage: '',
      error: null,

      // Actions
      sendMessage: async (prompt: string) => {
        try {
          set({ isStreaming: true, error: null });
          
          // Add user message
          const userMessage: ChatMessage = {
            role: 'user',
            content: prompt,
            timestamp: new Date().toISOString(),
          };
          
          set((state) => ({
            messages: [...state.messages, userMessage],
          }));

          // Get AI response
          const response = await aiApi.ask({ prompt });
          
          // Add assistant message
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: response.answer,
            timestamp: new Date().toISOString(),
          };
          
          set((state) => ({
            messages: [...state.messages, assistantMessage],
            isStreaming: false,
          }));
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to send message',
            isStreaming: false,
          });
          throw error;
        }
      },

      sendMessageStream: async (prompt: string) => {
        try {
          set({ isStreaming: true, error: null, currentStreamMessage: '' });
          
          // Add user message
          const userMessage: ChatMessage = {
            role: 'user',
            content: prompt,
            timestamp: new Date().toISOString(),
          };
          
          set((state) => ({
            messages: [...state.messages, userMessage],
          }));

          // Stream AI response
          await aiApi.askStream({
            prompt,
            onChunk: (chunk: string) => {
              set((state) => ({
                currentStreamMessage: state.currentStreamMessage + chunk,
              }));
            },
            onComplete: () => {
              const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: get().currentStreamMessage,
                timestamp: new Date().toISOString(),
              };
              
              set((state) => ({
                messages: [...state.messages, assistantMessage],
                isStreaming: false,
                currentStreamMessage: '',
              }));
            },
            onError: (error: Error) => {
              set({
                error: error.message,
                isStreaming: false,
                currentStreamMessage: '',
              });
            },
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to send message',
            isStreaming: false,
            currentStreamMessage: '',
          });
          throw error;
        }
      },

      fetchChatHistory: async () => {
        try {
          const response = await aiApi.getChatHistory();
          set({ messages: response.messages });
        } catch (error) {
          console.error('Failed to fetch chat history:', error);
        }
      },

      clearChatHistory: async () => {
        try {
          await aiApi.clearChatHistory();
          set({ messages: [] });
        } catch (error) {
          console.error('Failed to clear chat history:', error);
          throw error;
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setStreaming: (streaming: boolean) => {
        set({ isStreaming: streaming });
      },
    }),
    {
      name: 'ai-chat-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        messages: state.messages,
      }),
    }
  )
);