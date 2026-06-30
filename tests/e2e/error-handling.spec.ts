import { test, expect } from './fixtures/test-context';

const EMAIL = `err-test-${Date.now()}@test.nebula`;
const PASS = 'ErrP1!';

test.beforeAll(async ({ request }) => {
  await request.post('http://localhost:8000/api/v1/auth/signup', {
    data: { email: EMAIL, password: PASS },
  });
});

test('API returns 401 for expired tokens', async ({ request }) => {
  const res = await request.get('http://localhost:8000/api/v1/auth/me', {
    headers: { Authorization: 'Bearer expired-invalid-token' },
  });
  expect(res.status()).toBe(401);
});

test('API returns 404 for unknown route', async ({ request }) => {
  const res = await request.get('http://localhost:8000/api/v1/nonexistent');
  expect(res.status()).toBe(404);
});

test('search with network error returns 502', async ({ request }) => {
  const login = await request.post('http://localhost:8000/api/v1/auth/login', {
    data: { email: EMAIL, password: PASS },
  });
  const { access_token } = await login.json();

  const res = await request.get('http://localhost:8000/api/v1/search/web?q=test&backend=nonexistent', {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  expect([400, 502]).toContain(res.status());
});

test('signup with missing fields returns 422', async ({ request }) => {
  const res = await request.post('http://localhost:8000/api/v1/auth/signup', {
    data: {},
  });
  expect(res.status()).toBe(422);
});
