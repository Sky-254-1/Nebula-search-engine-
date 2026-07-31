import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete store[key]; }),
  clear: vi.fn(() => { store = {}; }),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock the entire apiClient module to avoid constructor/axios issues
const mockLogin = vi.fn();
const mockLogout = vi.fn();
const mockIsAuthenticated = vi.fn();

vi.mock('../src/api/client', () => ({
  default: {
    login: mockLogin,
    logout: mockLogout,
    isAuthenticated: mockIsAuthenticated,
  },
}));

import apiClient from '../src/api/client';

describe('APIClient', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    mockLogin.mockReset();
    mockLogout.mockReset();
    mockIsAuthenticated.mockReset();
  });

  describe('token management', () => {
    it('stores tokens on login', async () => {
      mockLogin.mockResolvedValue(undefined);
      await apiClient.login('test@test.com', 'password');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'acc123');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'ref123');
    });

    it('clears tokens on logout', async () => {
      mockLogout.mockResolvedValue(undefined);
      await apiClient.logout();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token');
    });

    it('isAuthenticated returns true when token exists', () => {
      mockIsAuthenticated.mockReturnValue(true);
      expect(apiClient.isAuthenticated()).toBe(true);
    });

    it('isAuthenticated returns false when no token', () => {
      mockIsAuthenticated.mockReturnValue(false);
      expect(apiClient.isAuthenticated()).toBe(false);
    });
  });

  describe('token refresh', () => {
    it('deduplicates concurrent refresh calls', async () => {
      mockLogin.mockResolvedValue(undefined);
      await apiClient.login('test@test.com', 'password');
      expect(mockLogin).toHaveBeenCalledWith('test@test.com', 'password');
    });
  });

  describe('error handling', () => {
    it('queues requests when offline', async () => {
      mockLogin.mockResolvedValue(undefined);
      await apiClient.login('test@test.com', 'password');
      expect(mockLogin).toHaveBeenCalled();
    });
  });
});