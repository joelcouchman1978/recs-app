import { test, expect } from '@playwright/test'

test('onboarding page renders', async ({ page }) => {
  await page.goto('/onboarding')
  await expect(page.locator('h1')).toHaveText(/Onboarding/i)
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
})

