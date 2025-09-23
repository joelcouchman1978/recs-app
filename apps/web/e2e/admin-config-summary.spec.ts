import { test, expect } from '@playwright/test'

test('admin config summary shows', async ({ page }) => {
  await page.goto('/admin')
  const card = page.locator('[data-test=admin-config-summary]')
  await expect(card).toBeVisible()
})

