import { test, expect } from "@playwright/test";

test("season-consistent chip appears when backend marks true", async ({ page }) => {
  await page.route("**/recommendations**", async (route) => {
    const res = await route.fetch();
    const ct = res.headers()["content-type"] || "";
    if (!ct.includes("application/json")) return route.continue();
    const body = await res.json();
    if (Array.isArray(body) && body.length > 0) {
      body[0] = {
        ...body[0],
        availability: { ...(body[0].availability || {}), season_consistent: true },
      };
      return route.fulfill({ json: body, status: 200, headers: res.headers() });
    }
    return route.continue();
  });

  await page.goto("/?seed=777");
  const anyCard = page.locator("[data-test=rec-card]").first();
  await expect(anyCard).toBeVisible();
  const chip = page.locator('[data-test="chip-season-match"]').first();
  await expect(chip).toBeVisible();
  await expect(chip).toHaveText("Season match");
});
