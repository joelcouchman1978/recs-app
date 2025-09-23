import { test, expect } from '@playwright/test'

test('profiles page renders and has save button', async ({ page }) => {
  await page.goto('/profiles')
  await expect(page.locator('h1')).toHaveText(/Profiles & Boundaries/i)
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
})

