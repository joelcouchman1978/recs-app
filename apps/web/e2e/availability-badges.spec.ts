import { test, expect } from "@playwright/test";

test("availability row renders when data present", async ({ page }) => {
  await page.goto("/?seed=101");
  const row = page.locator("[data-test=rec-availability]").first();
  await expect(row).toBeVisible();
});

