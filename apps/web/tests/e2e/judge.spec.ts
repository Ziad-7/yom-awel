import { expect, test, type Page } from "@playwright/test";
import { copy, expectAccessible, expectNoHorizontalScroll, onboard, shot } from "./flow";

async function trySample(page: Page, title: string) {
  const escaped = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await page.getByRole("button", { name: new RegExp(escaped) }).click();
  await expect(page.locator("#result-heading")).toBeFocused();
}

test("English judge: the five-step tour runs on one-click samples through the real evaluator", async ({ page }) => {
  const t = copy.en;
  const steps = t.judge.tour.steps;
  await onboard(page, "Judge", "en");
  const tour = page.getByRole("region", { name: t.judge.tour.title });
  await expect(tour).toContainText(t.judge.tour.progress(0, 5));
  await expectAccessible(page);
  await page.screenshot({ path: shot("judge-en-catalogue"), fullPage: true });

  await tour.getByRole("button", { name: t.judge.tour.go }).click();
  const samples = page.getByRole("region", { name: t.judge.title });
  await expect(samples.getByRole("button")).toHaveCount(4);
  await expect(page.getByRole("heading", { level: 3, name: t.mission.title })).toBeVisible();
  await expect(page.locator(".mission-checks li")).toHaveCount(4);
  await expect(page.locator(".full-brief")).not.toHaveAttribute("open");
  await expect(samples).toContainText(t.judge.outcome.retry(75));
  await trySample(page, t.judge.samples.duplicates_left.title);
  await expect(page.locator(".score bdi")).toHaveText("75");
  await expect(page.getByRole("region", { name: t.insights.xrayTitle })).toBeVisible();
  await expect(tour.locator("li.done")).toContainText(steps.mistake.title);
  const feedback = page.locator(".feedback-card");
  await expect(feedback.locator(".feedback-section")).toHaveCount(4);
  await expect(feedback.locator(".feedback-section.is-decision")).toHaveClass(/rework/);
  await expect(feedback.getByRole("heading", { level: 3, name: t.feedback.sections.impact })).toBeVisible();
  await page.screenshot({ path: shot("judge-en-duplicates"), fullPage: true });

  await trySample(page, t.judge.samples.fully_cleaned.title);
  await expect(page.locator(".score bdi")).toHaveText("100");
  await expect(page.getByRole("region", { name: t.judge.title })).toHaveCount(0);
  await expect(tour).toContainText(t.judge.tour.progress(2, 5));

  await tour.getByRole("button", { name: t.judge.tour.go }).click();
  await expect(page.getByRole("heading", { level: 1, name: "SQL sales report" })).toBeVisible();
  await trySample(page, t.judge.samples.hard_coded.title);
  await expect(page.getByRole("note")).toContainText(t.insights.sql.robustnessTitle);

  await tour.getByRole("button", { name: t.judge.tour.go }).click();
  await trySample(page, t.judge.samples.wrong_date_reply.title);
  await expect(page.locator(".score bdi")).toHaveText("75");
  await expect(page.locator(".email-checklist li.missing")).toContainText(t.insights.email.elements.updated_date);

  await tour.getByRole("button", { name: t.judge.tour.go }).click();
  await expect(page.getByRole("heading", { level: 1, name: t.headings.skills })).toBeVisible();
  const finished = page.getByRole("region", { name: t.judge.tour.title });
  await expect(finished).toContainText(t.judge.tour.complete);
  await expect(finished).toContainText(t.judge.tour.progress(5, 5));
  await expectAccessible(page);
  await page.screenshot({ path: shot("judge-en-complete"), fullPage: true });

  const attempts = await (await page.request.get("/api/v1/attempts")).json();
  const scores = attempts.map((attempt: { evaluation: { score: number } }) => attempt.evaluation.score);
  expect(scores.sort((a: number, b: number) => a - b)).toEqual([25, 75, 75, 100]);
});

test("Arabic judge on a 390px phone: samples fit and a rejected sample explains itself", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const t = copy.ar;
  await onboard(page, "لجنة", "ar");
  await page.getByRole("region", { name: t.judge.tour.title }).getByRole("button", { name: t.judge.tour.go }).click();
  await trySample(page, t.judge.samples.column_deleted.title);
  await expect(page.locator("#result-heading")).toHaveText(t.result.rejectedTitle);
  await expect(page.getByText(t.rejections.missing_columns)).toBeVisible();
  await expectNoHorizontalScroll(page);
  await expectAccessible(page);
  await page.screenshot({ path: shot("judge-ar-mobile"), fullPage: true });
});
