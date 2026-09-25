import { expect, test } from "@playwright/test";
import { copy, expectDocumentLanguage, expectNoHorizontalScroll, onboard, openCleanSales, shot, submitFile, demoFile } from "./flow";
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

test("Start over creates a new learner with no inherited progress", async ({ page }) => {
  await onboard(page, "First learner", "en");
  const first = await (await page.request.get("/api/v1/learners/me")).json();
  await openCleanSales(page, "en");
  await submitFile(page, "en", demoFile("sales_cleaned.csv"));
  await expect(page.locator("#result-heading")).toHaveText(copy.en.result.passTitle);

  await page.getByRole("button", { name: copy.en.restart.open }).click();
  await page.getByRole("button", { name: copy.en.restart.confirm }).click();
  await expect(page.getByLabel(copy.en.onboarding.nameLabel, { exact: true })).toBeVisible();
  await page.getByLabel(copy.en.onboarding.nameLabel, { exact: true }).fill("Second learner");
  await page.getByRole("button", { name: copy.en.onboarding.submit }).click();
  await expect(page.getByRole("heading", { level: 1, name: copy.en.headings.greeting("Second learner") })).toBeVisible();
  const second = await (await page.request.get("/api/v1/learners/me")).json();
  expect(second.learner_id).not.toBe(first.learner_id);
  expect(await (await page.request.get("/api/v1/attempts")).json()).toEqual([]);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: copy.en.headings.greeting("Second learner") })).toBeVisible();
});
