import { test, expect } from '@playwright/test'

test('family banner shows strong or warning', async ({ page }) => {
  await page.goto('/?seed=55')
  // Switch to family profile
  await page.getByRole('button', { name: 'family' }).click()
  const bannerWrap = page.locator('[data-test=family-coverage]')
  await expect(bannerWrap).toBeVisible()
  const strong = page.locator('[data-test=family-strong-banner]')
  const warn = page.locator('[data-test=family-warning-banner]')
  expect((await strong.count()) + (await warn.count())).toBeGreaterThan(0)
})

