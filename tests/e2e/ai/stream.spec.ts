import { test, expect } from '../fixtures/auth.fixture';
import { env } from '../config/env';

test.describe('AI disconnect recovery', () => {
  test('stream can be aborted and history still loads', async ({ request, accessToken }) => {
    const controller = new AbortController();
    const streamPromise = request.post(`${env.apiURL}/api/v1/ai/ask/stream`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { prompt: 'disconnect recovery test' },
      signal: controller.signal,
    });
    controller.abort();
    try {
      await streamPromise;
    } catch {
      // expected on abort
    }
    const history = await request.get(`${env.apiURL}/api/v1/ai/chat/history`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(history.ok()).toBeTruthy();
  });
});
