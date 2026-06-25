import { test, expect } from '../fixtures/auth.fixture';
import { env } from '../config/env';

test.describe('Token refresh', () => {
  test('refresh token returns new access token', async ({ request, testEmail, testPassword }) => {
    await request.post(`${env.apiURL}/api/v1/auth/signup`, {
      data: { email: testEmail, password: testPassword },
    });
    const login = await request.post(`${env.apiURL}/api/v1/auth/login`, {
      data: { email: testEmail, password: testPassword },
    });
    const { refresh_token, access_token } = await login.json();
    expect(access_token).toBeTruthy();
    expect(refresh_token).toBeTruthy();

    const refresh = await request.post(`${env.apiURL}/api/v1/auth/refresh`, {
      data: { refresh_token },
    });
    expect(refresh.ok()).toBeTruthy();
    const refreshed = await refresh.json();
    expect(refreshed.access_token).toBeTruthy();
    expect(refreshed.refresh_token).toBeTruthy();
  });

  test('logout invalidates refresh token', async ({ request, testEmail, testPassword }) => {
    await request.post(`${env.apiURL}/api/v1/auth/signup`, {
      data: { email: testEmail, password: testPassword },
    });
    const login = await request.post(`${env.apiURL}/api/v1/auth/login`, {
      data: { email: testEmail, password: testPassword },
    });
    const { refresh_token } = await login.json();
    await request.post(`${env.apiURL}/api/v1/auth/logout`, {
      data: { refresh_token },
    });
    const refresh = await request.post(`${env.apiURL}/api/v1/auth/refresh`, {
      data: { refresh_token },
    });
    expect(refresh.status()).toBe(401);
  });
});
