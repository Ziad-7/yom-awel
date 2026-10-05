import { expect, test } from "@playwright/test";
import { copy, demoFile, expectAccessible, expectNoHorizontalScroll, onboard, openCleanSales, shot, submitFile } from "./flow";

test("English: a retry shows what was fixed, the cost recovered and the score trend", async ({ page }) => {
  const t = copy.en;
  await onboard(page, "Progress learner", "en");
  await openCleanSales(page, "en");
  await submitFile(page, "en", demoFile("sales_retry_half.xlsx"));
  await expect(page.getByRole("region", { name: /Progress since/ })).toHaveCount(0);

  await submitFile(page, "en", demoFile("sales_retry_duplicates.csv"));
  const card = page.getByRole("region", { name: t.progress.title(1) });
  await expect(card).toContainText(t.progress.up(25));
  await expect(card).toContainText(t.progress.change(50, 75));
  await expect(card.locator("li.fixed")).toHaveCount(2);
  await expect(card.locator("li.regressed")).toContainText(t.checks.unique_orders.title);
  await expect(card.locator("li.regressed")).toContainText(t.progress.issues(0, 10));
  await expect(card.locator(".progress-metrics li.worse")).toContainText(t.insights.metrics.revenue_overstated.label);

  await submitFile(page, "en", demoFile("sales_cleaned.csv"));
  const last = page.getByRole("region", { name: t.progress.title(2) });
  await expect(last).toContainText(t.progress.change(75, 100));
  await expect(last.locator("li.fixed")).toContainText(t.progress.issues(10, 0));
  await expect(last.locator(".progress-metrics li.better")).toContainText(/EGP\s?16,956\.47 → EGP\s?0/);
  await expect(last.getByRole("img")).toHaveCount(3);
  await last.getByRole("img").nth(1).focus();
  await expect(last.locator(".chart-tooltip")).toHaveText(t.progress.point(2, 75, false));
  await expectAccessible(page);
  await last.screenshot({ path: shot("progress-en") });
});

test("Arabic, 390px: the progress card fits and reads right to left", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const t = copy.ar;
  await onboard(page, "مريم", "ar");
  await openCleanSales(page, "ar");
  await submitFile(page, "ar", demoFile("sales_rejected_missing_columns.csv"));
  await submitFile(page, "ar", demoFile("sales_retry_duplicates.csv"));
  const card = page.getByRole("region", { name: t.progress.title(1) });
  await expect(card).toContainText(t.progress.wasRejected);
  await expect(card).toContainText(t.progress.up(75));
  await expectNoHorizontalScroll(page);
  await expectAccessible(page);
  await card.screenshot({ path: shot("progress-ar-mobile") });
});
