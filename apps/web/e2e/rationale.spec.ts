import { test, expect } from '@playwright/test'

test('rationales render and are non-empty (seeded)', async ({ page }) => {
  await page.goto('/?seed=314')

  const cards = page.locator('[data-test=rec-card]')
  await expect(cards.first()).toBeVisible()

  const rationales = page.locator('[data-test=rec-rationale]')
  await expect(rationales.first()).toBeVisible()

  const count = await rationales.count()
  expect(count).toBeGreaterThan(0)

  for (let i = 0; i < Math.min(count, 10); i++) {
    const txt = (await rationales.nth(i).textContent())?.trim() || ''
    expect(txt.length).toBeGreaterThan(0)
    expect(txt.length).toBeLessThanOrEqual(180)
  }
})

