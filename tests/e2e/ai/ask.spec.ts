import { test, expect } from '../fixtures/auth.fixture';
import { env } from '../config/env';

test.describe('AI', () => {
  test('ask endpoint returns answer', async ({ request, accessToken }) => {
    const res = await request.post(`${env.apiURL}/api/v1/ai/ask`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { prompt: 'What is Nebula Search?' },
    });
    if (res.status() === 404) {
      test.skip();
    }
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.answer).toBeTruthy();
  });

  test('chat history restore', async ({ request, accessToken }) => {
    await request.post(`${env.apiURL}/api/v1/ai/ask`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { prompt: 'Hello Nebula' },
    });
    const history = await request.get(`${env.apiURL}/api/v1/ai/chat/history`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(history.ok()).toBeTruthy();
    const body = await history.json();
    expect(body.messages.length).toBeGreaterThan(0);
  });

  test('stream endpoint emits chunks', async ({ request, accessToken }) => {
    const res = await request.post(`${env.apiURL}/api/v1/ai/ask/stream`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { prompt: 'Stream test' },
    });
    expect(res.ok()).toBeTruthy();
    const text = await res.text();
    expect(text.length).toBeGreaterThan(0);
  });
});
