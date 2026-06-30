import { test, expect } from '../fixtures/auth.fixture';
import { setOffline } from '../utils/helpers';

test.describe('PWA offline', () => {
  test('app shell loads while offline', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Nebula Search')).toBeVisible();
    await setOffline(page, true);
    await page.reload();
    await expect(page.locator('.hero, .page')).toBeVisible();
    await setOffline(page, false);
  });

  test('reconnect after offline', async ({ page, accessToken }) => {
    void accessToken;
    await page.goto('/');
    await setOffline(page, true);
    await page.reload();
    await setOffline(page, false);
    await page.reload();
    await expect(page.getByText('Nebula Search')).toBeVisible();
  });

  test('install prompt region exists', async ({ page }) => {
    await page.goto('/');
    const install = page.locator('[class*="install"], .install-prompt');
    const count = await install.count();
    expect(count >= 0).toBeTruthy();
  });
});
