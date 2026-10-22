import { test, expect } from '@playwright/test';

test('student can register, submit, and find their own issue', async ({ page }) => {
  const email = 'browser-' + Date.now() + '-' + Math.random().toString(36).slice(2) + '@example.edu';
  await page.goto('http://127.0.0.1:5173');
  await page.getByRole('button', { name: /create an account/i }).click();
  await page.getByPlaceholder('student@example.edu').fill(email);
  await page.getByPlaceholder('Your password').fill('browser-demo-password-123');
  const response = page.waitForResponse(r => r.url().includes('/auth/register') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create account' }).click();
  const registration = await response;
  expect(registration.status(), 'registration API response: ' + await registration.text()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Campus issue board' })).toBeVisible();
  await page.getByRole('button', { name: /report an issue/i }).click();
  await expect(page.getByRole('heading', { name: 'Report a campus issue' })).toBeVisible();
  await page.getByPlaceholder('e.g. Water cooler not working').fill('Library wifi is unavailable');
  await page.getByPlaceholder('Describe what happened...').fill('Wifi network is down near the library desks');
  await page.getByPlaceholder('e.g. Block B, Ground Floor').fill('Library');
  await page.getByRole('button', { name: /submit report/i }).click();
  await expect(page.getByRole('heading', { name: 'Library wifi is unavailable' })).toBeVisible();
});
