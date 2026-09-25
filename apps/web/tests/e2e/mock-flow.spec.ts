import { expect, test, type Page } from "@playwright/test";
import type { EvaluationResult } from "../../src/lib/api/contract";
import { createMockApi, evaluation } from "../../src/test/mock-api";
import {
  copy,
  expectAccessible,
  expectDocumentLanguage,
  expectNoHorizontalScroll,
  onboard,
  openCleanSales,
  shot,
  submitFile,
  toggleFeedback,
} from "./flow";

const csv = (name: string) => ({ name, mimeType: "text/csv", buffer: Buffer.from("order_id\n1\n") });

/** Serves /api/v1 from the typed contract mock inside the browser context. */
async function mockApi(
  page: Page,
  outcome: EvaluationResult,
  options: { deferSubmission?: boolean; failFirstPoll?: boolean } = {},
) {
  const api = createMockApi(outcome, options);
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const response = await api.fetch(url.pathname + url.search, {
      method: request.method(),
      headers: request.headers(),
      body: request.postData() ?? undefined,
    });
    await route.fulfill({ status: response.status, contentType: "application/json", body: await response.text() });
  });
  return api;
}

test("Arabic: onboarding, catalogue, pass, feedback toggle, skills", async ({ page }) => {
  const api = await mockApi(page, evaluation());
  const t = copy.ar;
  const response = await page.goto("/");
  expect(response!.headers()["content-security-policy"]).toBe("frame-ancestors 'none'");
  expect(response!.headers()["x-frame-options"]).toBe("DENY");
  await expectAccessible(page);
  await page.screenshot({ path: shot("mock-ar-onboarding"), fullPage: true });
  await onboard(page, "سارة", "ar");
  await expect(page.locator(".task-tile")).toHaveCount(1);
  await expectAccessible(page);
  await page.screenshot({ path: shot("mock-ar-catalogue"), fullPage: true });
  await openCleanSales(page, "ar");
  await expect(page.locator("script", { hasText: "alert(1)" })).toHaveCount(0);
  await expect(page.getByText(t.workspace.critical, { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: t.workspace.downloadCsv })).toHaveAttribute(
    "href",
    "/api/v1/tasks/clean-sales/dataset?format=csv",
  );
  await expectAccessible(page);
  await page.screenshot({ path: shot("mock-ar-workspace"), fullPage: true });
  await submitFile(page, "ar", csv("sales_cleaned.csv"));
  await expect(page.locator("#result-heading")).toHaveText(t.result.passTitle);
  await expectAccessible(page);
  await toggleFeedback(page, "ar");
  await page.screenshot({ path: shot("mock-ar-result"), fullPage: true });
  await page.getByRole("button", { name: t.result.viewSkills }).click();
  await expect(page.getByRole("progressbar", { name: t.skills.names.data_cleaning })).toHaveAttribute("value", "100");
  await expectAccessible(page);
  const writes = api.calls.filter((call) => call.method !== "GET");
  expect(writes.every((call) => call.headers["x-yom-awel"] === "1")).toBe(true);
});

test("English: critical-check retry explains the 75, revision focuses the upload", async ({ page }) => {
  await mockApi(page, evaluation(["unique_orders"]));
  const t = copy.en;
  await onboard(page, "Sara", "en");
  await openCleanSales(page, "en");
  await submitFile(page, "en", csv("sales_retry_duplicates.csv"));
  await expect(page.getByText(t.result.criticalFailed(75, 75))).toBeVisible();
  await expectAccessible(page);
  await page.screenshot({ path: shot("mock-en-critical-retry"), fullPage: true });
  await page.getByRole("button", { name: t.result.uploadRevision }).click();
  await expect(page.locator("#submission")).toBeFocused();
});

test("English: evaluator rejection code", async ({ page }) => {
  await mockApi(page, evaluation([], ["missing_columns"]));
  const t = copy.en;
  await onboard(page, "Sara", "en");
  await openCleanSales(page, "en");
  await submitFile(page, "en", csv("sales_rejected_missing_columns.csv"));
  await expect(page.locator("#result-heading")).toHaveText(t.result.rejectedTitle);
  await expect(page.getByText(t.rejections.missing_columns)).toBeVisible();
});

test("a processing submission polls with its original idempotency key", async ({ page }) => {
  const api = await mockApi(page, evaluation(), { deferSubmission: true });
  await onboard(page, "Sara", "en");
  await openCleanSales(page, "en");
  await submitFile(page, "en", csv("sales_cleaned.csv"));
  await expect(page.locator("#result-heading")).toHaveText(copy.en.result.passTitle);
  const submission = api.calls.find((call) => call.method === "POST" && call.path === "/api/v1/submissions");
  const poll = api.calls.find((call) => call.method === "GET" && call.path.startsWith("/api/v1/submissions/"));
  expect(submission?.headers["idempotency-key"]).toBeTruthy();
  expect(poll?.headers["idempotency-key"]).toBe(submission?.headers["idempotency-key"]);
});

test("an interrupted submission resumes after reload with the same key", async ({ page }) => {
  const api = await mockApi(page, evaluation(), { deferSubmission: true, failFirstPoll: true });
  await onboard(page, "Sara", "en");
  await openCleanSales(page, "en");
  await page.locator("#submission").setInputFiles(csv("sales_cleaned.csv"));
  await page.getByRole("button", { name: copy.en.upload.submit }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: copy.en.catalogue.action.in_progress }).click();
  await expect(page.locator("#result-heading")).toHaveText(copy.en.result.passTitle);
  const submission = api.calls.find((call) => call.method === "POST" && call.path === "/api/v1/submissions");
  const polls = api.calls.filter((call) => call.method === "GET" && call.path.startsWith("/api/v1/submissions/"));
  expect(polls).toHaveLength(2);
  expect(polls.every((call) => call.headers["idempotency-key"] === submission?.headers["idempotency-key"])).toBe(true);
});

test("390px mobile: keyboard entry, language toggle, invalid upload", async ({ page }) => {
  await mockApi(page, evaluation());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: copy.ar.shell.skip })).toBeFocused();
  await page.getByRole("button", { name: copy.ar.language.switchLabel }).click();
  await expectDocumentLanguage(page, "en");
  await expectNoHorizontalScroll(page);
  await page.getByLabel(copy.en.onboarding.nameLabel, { exact: true }).fill("Omar");
  await page.getByLabel(copy.en.onboarding.nameLabel, { exact: true }).press("Enter");
  await openCleanSales(page, "en");
  await page
    .locator("#submission")
    .setInputFiles({ name: "bad.exe", mimeType: "application/octet-stream", buffer: Buffer.from("x") });
  await expect(page.getByRole("alert").filter({ hasText: copy.en.rejections.unsupported_type })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await expectAccessible(page);
  await page.screenshot({ path: shot("mock-en-mobile-workspace"), fullPage: true });
  await page.getByRole("button", { name: copy.en.language.switchLabel }).click();
  await expectDocumentLanguage(page, "ar");
  await expectNoHorizontalScroll(page);
  await page.screenshot({ path: shot("mock-ar-mobile-workspace"), fullPage: true });
});
