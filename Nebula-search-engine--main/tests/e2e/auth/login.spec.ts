import { test, expect } from '../fixtures/auth.fixture';
import { openAuthModal, fillAuthForm } from '../utils/helpers';

test.describe('Authentication', () => {
  test('signup and login', async ({ page, testEmail, testPassword }) => {
    await page.goto('/');
    await openAuthModal(page);
    await page.getByRole('button', { name: 'Need an account? Sign up' }).click();
    await fillAuthForm(page, testEmail, testPassword);
    await page.getByRole('button', { name: 'Sign up' }).click();
    await expect(page.getByText(testEmail)).toBeVisible({ timeout: 15000 });
  });

  test('login with existing user', async ({ page, testEmail, testPassword, accessToken }) => {
    void accessToken;
    await page.goto('/');
    await openAuthModal(page);
    await fillAuthForm(page, testEmail, testPassword);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByText(testEmail)).toBeVisible({ timeout: 15000 });
  });

  test('logout', async ({ page, testEmail, testPassword, accessToken }) => {
    void accessToken;
    await page.goto('/');
    await openAuthModal(page);
    await fillAuthForm(page, testEmail, testPassword);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByText(testEmail)).toBeVisible();
    await page.getByRole('button', { name: 'Log out' }).click();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  });
});
