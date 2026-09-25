import { expect, test } from "@playwright/test";
import { copy, expectDocumentLanguage, expectNoHorizontalScroll, onboard, openCleanSales, shot } from "./flow";
import { demoJourney } from "./journey";

test("Arabic, CSV: rejection, critical retry, feedback in English, pass, progress", async ({ page }) => {
  await demoJourney(page, "ar", { format: "csv", audit: true, pause: 0 });
});

test("English, XLSX: partial retry, feedback in Arabic, pass, progress", async ({ page }) => {
  await demoJourney(page, "en", { format: "xlsx", audit: true, pause: 0 });
});

test("the language toggle saves the learner's language and survives a reload", async ({ page }) => {
  await onboard(page, "Sara", "en");
  const saved = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/learners/me/language") && response.ok(),
  );
  await page.getByRole("button", { name: copy.en.language.switchLabel }).click();
  expect((await saved).request().headers()["x-yom-awel"]).toBe("1");
  await page.reload();
  await expectDocumentLanguage(page, "ar");
  await expect(page.getByRole("heading", { level: 1, name: copy.ar.headings.greeting("Sara") })).toBeVisible();
});

test("390px mobile workspace against the real API", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await onboard(page, "عمر", "ar");
  await openCleanSales(page, "ar");
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: shot("ar-mobile-workspace"), fullPage: true });
});
