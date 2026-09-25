import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { copy, expectAccessible, expectDocumentLanguage, expectNoHorizontalScroll, onboard } from "./flow";

const source = path.dirname(fileURLToPath(import.meta.url));

async function openTask(page: import("@playwright/test").Page, taskId: string) {
  await page.locator(`[aria-labelledby="task-${taskId}"]`).getByRole("button").click();
  await expect(page.locator("#submission-answer")).toBeVisible();
}

test("one learner completes SQL and client email, then reviews each result", async ({ page }) => {
  await onboard(page, "Three-task learner", "en");
  await expect(page.locator(".task-tile")).toHaveCount(3);

  await openTask(page, "sql-report");
  await page.locator("#submission-answer").fill(
    "SELECT region, COUNT(*) AS paid_orders, ROUND(SUM(quantity * unit_price), 2) AS total_revenue " +
    "FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;",
  );
  await page.getByRole("button", { name: /Submit for review/ }).click();
  await expect(page.locator("#result-heading")).toHaveText("Great work! Your submission passed.");
  await page.getByRole("button", { name: /Back to tasks/ }).click();
  await openTask(page, "client-email");
  const email = readFileSync(path.resolve(source, "../../../../task_packages/client-email/1/examples/pass.en.txt"), "utf8");
  await page.locator("#submission-answer").fill(email);
  await page.getByRole("button", { name: /Submit for review/ }).click();
  await expect(page.locator("#result-heading")).toHaveText("Great work! Your submission passed.");

  await page.getByRole("button", { name: /Skills & progress/ }).click();
  await expect(page.locator(".status-list")).toContainText("SQL sales report");
  await expect(page.locator(".status-list")).toContainText("Write a customer update email");
  const history = page.locator(".attempt-timeline li");
  await expect(history).toHaveCount(2);
  await history.filter({ hasText: "Write a customer update email" }).getByRole("button").click();
  await expect(page.getByRole("heading", { level: 1, name: "Write a customer update email" })).toBeVisible();
  await page.getByRole("button", { name: /Skills & progress/ }).click();
  await page.locator(".attempt-timeline li").filter({ hasText: "SQL sales report" }).getByRole("button").click();
  await expect(page.getByRole("heading", { level: 1, name: "SQL sales report" })).toBeVisible();
  const attempts = await (await page.request.get("/api/v1/attempts")).json();
  expect(attempts).toHaveLength(2);
  expect(attempts.map((attempt: { evaluation: { passed: boolean } }) => attempt.evaluation.passed)).toEqual([true, true]);
});

test("Arabic mobile learner completes SQL and email with accessible result", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await onboard(page, "سارة", "ar");
  await openTask(page, "sql-report");
  await page.locator("#submission-answer").fill(
    "SELECT region, COUNT(*) AS paid_orders, ROUND(SUM(quantity * unit_price), 2) AS total_revenue " +
    "FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;",
  );
  await page.getByRole("button", { name: copy.ar.upload.submit }).click();
  await expect(page.locator(".score bdi")).toHaveText("100");
  await page.getByRole("button", { name: copy.ar.workspace.back }).click();
  await openTask(page, "client-email");
  const email = readFileSync(path.resolve(source, "../../../../task_packages/client-email/1/examples/pass.ar-EG.txt"), "utf8");
  await page.locator("#submission-answer").fill(email);
  await page.getByRole("button", { name: copy.ar.upload.submit }).click();
  await expect(page.locator(".score bdi")).toHaveText("100");
  await expectDocumentLanguage(page, "ar");
  await expectNoHorizontalScroll(page);
  await expectAccessible(page);
});

test("a pending SQL result settles before switching to email", async ({ page }) => {
  await onboard(page, "Pending learner", "en");
  await openTask(page, "sql-report");
  let submissionId = "";
  await page.route("**/api/v1/submissions", async (route) => {
    const response = await route.fetch();
    const outcome = await response.json();
    submissionId = outcome.submission_id;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ submission_id: submissionId, status: "PROCESSING", retry_after_seconds: 0 }),
    });
  });
  let firstPoll = true;
  await page.route("**/api/v1/submissions/*", async (route) => {
    if (route.request().method() === "GET" && firstPoll) {
      firstPoll = false;
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "evaluation_failed" }) });
    } else await route.continue();
  });
  await page.locator("#submission-answer").fill(
    "SELECT region, COUNT(*) AS paid_orders, ROUND(SUM(quantity * unit_price), 2) AS total_revenue " +
    "FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;",
  );
  await page.getByRole("button", { name: /Submit for review/ }).click();
  await expect.poll(() => submissionId).not.toBe("");
  await expect(page.getByRole("button", { name: /Check result/ })).toBeVisible();
  await page.getByRole("button", { name: /Back to tasks/ }).click();
  await openTask(page, "client-email");
  await expect(page.locator("#result-heading")).toHaveCount(0);
  const email = readFileSync(path.resolve(source, "../../../../task_packages/client-email/1/examples/pass.en.txt"), "utf8");
  await page.locator("#submission-answer").fill(email);
  await page.getByRole("button", { name: /Submit for review/ }).click();
  await expect(page.locator("#result-heading")).toHaveText("Great work! Your submission passed.");
  await expect(page.locator(".score bdi")).toHaveText("100");
});
