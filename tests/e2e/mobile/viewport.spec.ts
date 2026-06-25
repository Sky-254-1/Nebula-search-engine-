import { test, expect } from '../fixtures/auth.fixture';

test.describe('Mobile viewport', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('responsive layout on mobile', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Nebula Search')).toBeVisible();
    const searchBar = page.locator('.search-bar');
    await expect(searchBar).toBeVisible();
    const box = await searchBar.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(390);
  });

  test('header actions accessible', async ({ page }) => {
    await page.goto('/');
    const signIn = page.getByRole('button', { name: 'Sign in' });
    await expect(signIn).toBeVisible();
  });

  test('touch scroll on results', async ({ page, accessToken }) => {
    void accessToken;
    await page.goto('/');
    await page.getByLabel('Search query').fill('mobile test');
    await page.getByRole('button', { name: 'Search' }).click();
    await page.waitForTimeout(8000);
    await page.mouse.wheel(0, 300);
    await expect(page.locator('.hero')).toBeVisible();
  });
});
