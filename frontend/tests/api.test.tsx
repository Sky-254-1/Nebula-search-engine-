import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock axios before importing apiClient
vi.mock('axios', () => {
  const mockAxiosInstance = {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock navigator.onLine
Object.defineProperty(navigator, 'onLine', { value: true, writable: true });

import apiClient from '../src/api/client';

describe('APIClient', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('token management', () => {
    it('stores tokens on login', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { access_token: 'acc123', refresh_token: 'ref123', expires_in: 3600 },
      });
      // Access the axios instance mock
      const axios = await import('axios');
      const instance = (axios.default.create as any)();
      instance.post = mockPost;

      await apiClient.login('test@test.com', 'password');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'acc123');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'ref123');
    });

    it('clears tokens on logout', async () => {
      localStorageMock.getItem.mockReturnValue('ref123');
      const mockPost = vi.fn().mockResolvedValue({ data: {} });
      const axios = await import('axios');
      const instance = (axios.default.create as any)();
      instance.post = mockPost;

      await apiClient.logout();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });

    it('isAuthenticated returns true when token exists', () => {
      localStorageMock.getItem.mockReturnValue('some-token');
      expect(apiClient.isAuthenticated()).toBe(true);
    });

    it('isAuthenticated returns false when no token', () => {
      localStorageMock.getItem.mockReturnValue(null);
      expect(apiClient.isAuthenticated()).toBe(false);
    });
  });

  describe('token refresh', () => {
    it('deduplicates concurrent refresh calls', async () => {
      localStorageMock.getItem.mockReturnValue('ref123');
      const mockPost = vi.fn().mockResolvedValue({
        data: { access_token: 'new-acc', refresh_token: 'new-ref', expires_in: 3600 },
      });
      const axios = await import('axios');
      const instance = (axios.default.create as any)();
      instance.post = mockPost;

      // Call refresh twice concurrently
      const [r1, r2] = await Promise.all([
        (apiClient as any).refreshAccessToken(),
        (apiClient as any).refreshAccessToken(),
      ]);

      // Only one actual POST should happen
      expect(mockPost).toHaveBeenCalledTimes(1);
      expect(r1).toBe('new-acc');
      expect(r2).toBe('new-acc');
    });
  });

  describe('error handling', () => {
    it('queues requests when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { value: false });
      localStorageMock.getItem.mockReturnValue('tok');

      const axios = await import('axios');
      const instance = (axios.default.create as any)();
      instance.get = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(apiClient.get('/search')).rejects.toThrow('Network error');
    });
  });
});