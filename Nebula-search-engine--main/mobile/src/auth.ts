import { Preferences } from '@capacitor/preferences';
import { config } from './config';

const TOKEN_KEY = 'nebula_tokens';

export async function saveTokens(tokens: { access_token: string; refresh_token?: string }) {
  await Preferences.set({ key: TOKEN_KEY, value: JSON.stringify(tokens) });
}

export async function loadTokens() {
  const { value } = await Preferences.get({ key: TOKEN_KEY });
  return value ? JSON.parse(value) : null;
}

export async function clearTokens() {
  await Preferences.remove({ key: TOKEN_KEY });
}

export async function restoreSession(apiBase: string) {
  const tokens = await loadTokens();
  if (!tokens?.access_token) return null;
  const res = await fetch(`${apiBase}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  if (!res.ok) {
    await clearTokens();
    return null;
  }
  return await res.json();
}
