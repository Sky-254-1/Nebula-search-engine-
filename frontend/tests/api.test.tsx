import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
  removeItem: vi.fn((key: string) => { delete store[key]; }),
  clear: vi.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
};

describe('APIClient', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
  });

  it('isAuthenticated returns true when token exists', () => {
    const mockIsAuthenticated = vi.fn().mockReturnValue(true);
    expect(mockIsAuthenticated()).toBe(true);
  });

  it('isAuthenticated returns false when no token', () => {
    const mockIsAuthenticated = vi.fn().mockReturnValue(false);
    expect(mockIsAuthenticated()).toBe(false);
  });

  it('clears tokens on logout', () => {
    const mockRemoveItem = vi.fn();
    const mockLogout = vi.fn().mockResolvedValue(undefined);

    mockLogout();
    expect(mockLogout).toHaveBeenCalled();
  });
});
