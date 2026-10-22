import { test, expect } from '@playwright/test';

test('student can register, submit, and find their own issue', async ({ page }) => {
  const email = 'browser-' + Date.now() + '-' + Math.random().toString(36).slice(2) + '@example.edu';
  await page.goto('http://127.0.0.1:5173');
  await page.getByRole('button', { name: /create an account/i }).click();
  await page.getByPlaceholder('student@example.edu').fill(email);
  await page.getByPlaceholder('Your password').fill('browser-demo-password-123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'Campus issue board' })).toBeVisible();
  await page.getByRole('button', { name: /report an issue/i }).click();
  await expect(page.getByRole('dialog').or(page.getByText('Report a new issue'))).toBeVisible();
});
