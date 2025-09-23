import { test, expect } from "@playwright/test";

test("same seed -> same top card across reloads", async ({ page }) => {
  await page.goto("/?seed=111");
  const title = page.locator("[data-test=rec-card-title]").first();

  await expect(title).toBeVisible();
  const t1 = (await title.textContent())?.trim();
  expect(t1).toBeTruthy();

  await page.reload();
  const t2 = (await title.textContent())?.trim();
  expect(t2).toBe(t1);
});

test("changing seed forwards to API (network assertion) and may change top card", async ({ page }) => {
  await page.goto("/?seed=222");
  const title = page.locator("[data-test=rec-card-title]").first();
  await expect(title).toBeVisible();
  const tA = (await title.textContent())?.trim();

  let sawSeed = false;
  await page.route("**/recommendations**", (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("seed") === "333") {
      sawSeed = true;
    }
    route.continue();
  });

  await page.goto("/?seed=333");

  await expect(page.locator("[data-test=rec-card]").first()).toBeVisible();
  expect(sawSeed).toBeTruthy();

  const tB = (await title.textContent())?.trim();
  expect(tB).toBeTruthy();
});

