import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import {
  copy,
  demoFile,
  expectAccessible,
  expectNoHorizontalScroll,
  onboard,
  openCleanSales,
  shot,
  submitFile,
} from "./flow";

const examples = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../task_packages/client-email/1/examples");
const HARDCODED_SQL = `SELECT 'Alexandria' AS region, 3 + (SELECT COUNT(order_id) FROM sales) * 0 AS paid_orders, 230 AS total_revenue
UNION ALL SELECT 'Aswan', 3, 150.5
UNION ALL SELECT 'Cairo', 4, 414.5
UNION ALL SELECT 'Giza', 4, 314`;

async function answer(page: Page, taskId: string, text: string) {
  await page.getByRole("button", { name: copy.en.workspace.back }).click();
  await page.locator(`[aria-labelledby="task-${taskId}"]`).getByRole("button").click();
  await page.locator("#submission-answer").fill(text);
  await page.getByRole("button", { name: copy.en.upload.submit }).click();
  await expect(page.locator("#result-heading")).toBeFocused();
}

test("English: the X-ray prices and pinpoints each task's mistakes from the real evaluator", async ({ page }) => {
  const t = copy.en.insights;
  await onboard(page, "X-ray learner", "en");
  await openCleanSales(page, "en");

  await submitFile(page, "en", demoFile("sales_retry_duplicates.csv"));
  const impact = page.getByRole("region", { name: t.impactTitle });
  await expect(impact.locator("li.cost")).toContainText(t.metrics.revenue_overstated.label);
  await expect(impact.locator("li.cost strong")).toContainText(/EGP\s?[1-9]/);
  const xray = page.getByRole("region", { name: t.xrayTitle });
  await expect(xray.locator("td.flagged").first()).toBeVisible();
  await expect(xray.locator("td.problems").first()).toContainText(/Duplicate order ID \(same as row \d+/);
  await expect(xray.getByRole("button", { name: /Unique orders/ })).toBeVisible();
  await expectAccessible(page);
  await page.screenshot({ path: shot("xray-en-sales-duplicates"), fullPage: true });

  await submitFile(page, "en", demoFile("sales_cleaned.xlsx"));
  await expect(page.getByRole("region", { name: t.impactTitle })).toContainText(t.impactClear);
  await expect(page.getByText(t.table.clean)).toBeVisible();

  await answer(page, "sql-report", HARDCODED_SQL);
  await expect(page.getByRole("note")).toContainText(t.sql.robustnessTitle);
  await expect(page.getByRole("region", { name: t.xrayTitle }).locator("tbody tr")).toHaveCount(4);
  await expectAccessible(page);
  await page.screenshot({ path: shot("xray-en-sql-hardcoded"), fullPage: true });

  await answer(page, "client-email", readFileSync(path.join(examples, "fail.en.txt"), "utf8"));
  const email = page.getByRole("region", { name: t.xrayTitle });
  await expect(email.locator(".email-checklist li.missing").first()).toBeVisible();
  await expect(email.getByText(`${copy.en.insights.email.missing}:`).first()).toBeAttached();
  await expect(page.getByRole("region", { name: t.impactTitle }).locator("li.cost")).toContainText(t.metrics.customer_questions_left_open.label);
  await expectAccessible(page);
  await page.screenshot({ path: shot("xray-en-email-fail"), fullPage: true });
});

test("Arabic, 390px: the X-ray of an XLSX retry fits the screen and stays accessible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const t = copy.ar.insights;
  await onboard(page, "مريم", "ar");
  await openCleanSales(page, "ar");
  await submitFile(page, "ar", demoFile("sales_retry_half.xlsx"));
  await expect(page.getByRole("region", { name: t.impactTitle }).locator("li.cost").first()).toBeVisible();
  const xray = page.getByRole("region", { name: t.xrayTitle });
  await expect(xray.locator("td.flagged").first()).toBeVisible();
  await expectNoHorizontalScroll(page);
  await expectAccessible(page);
  await page.screenshot({ path: shot("xray-ar-sales-mobile"), fullPage: true });
});

test("Arabic: the email X-ray highlights the learner's own words", async ({ page }) => {
  const t = copy.ar.insights;
  await onboard(page, "مريم", "ar");
  await page.locator('[aria-labelledby="task-client-email"]').getByRole("button").click();
  await page.locator("#submission-answer").fill(readFileSync(path.join(examples, "pass.ar-EG.txt"), "utf8"));
  await page.getByRole("button", { name: copy.ar.upload.submit }).click();
  await expect(page.locator("#result-heading")).toBeFocused();
  const xray = page.getByRole("region", { name: t.xrayTitle });
  await expect(xray.locator(".email-text mark").first()).toBeVisible();
  await xray.getByRole("button", { name: new RegExp(t.email.elements.refund_amount) }).click();
  await expect(xray.locator(".email-text mark.active")).toContainText("120");
  await expect(page.getByRole("region", { name: t.impactTitle })).toContainText(t.impactClear);
  await expectAccessible(page);
  await page.screenshot({ path: shot("xray-ar-email-pass"), fullPage: true });
});
