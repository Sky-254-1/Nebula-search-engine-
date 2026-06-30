import { test, expect } from '../fixtures/auth.fixture';
import { env } from '../config/env';

test.describe('Documents', () => {
  test('upload, index, and retrieve', async ({ request, accessToken }) => {
    const content = 'Nebula vector indexing test document content for retrieval.';
    const upload = await request.post(`${env.apiURL}/api/v1/storage/documents`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      multipart: {
        file: {
          name: 'test-doc.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from(content),
        },
      },
    });
    expect(upload.ok()).toBeTruthy();
    const doc = await upload.json();
    expect(doc.id).toBeTruthy();

    const indexNow = await request.post(
      `${env.apiURL}/api/v1/vector/documents/${doc.id}/index-now`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    expect(indexNow.ok()).toBeTruthy();

    const search = await request.post(`${env.apiURL}/api/v1/vector/search`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { query: 'vector indexing test', top_k: 5 },
    });
    expect(search.ok()).toBeTruthy();
    const results = await search.json();
    expect(results.total).toBeGreaterThan(0);
  });
});
