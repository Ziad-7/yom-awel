import { describe, expect, it } from "vitest";
import type { Attempt, TaskSummary } from "./api/contract";
import { nextStep, tourProgress } from "./tour";

const task = (task_id: string): TaskSummary => ({
  task_id,
  version: "1",
  task_version_id: `${task_id}-v1`,
  title_ar: task_id,
  title_en: task_id,
  status: "in_progress",
  pass_threshold: 75,
  points_total: 100,
});
const TASKS = ["clean-sales", "sql-report", "client-email"].map(task);
const attempt = (taskId: string, passed: boolean) =>
  ({ evaluation: { task_version_id: `${taskId}-v1`, passed } }) as Attempt;

describe("tourProgress", () => {
  it("starts at the first step", () => {
    const progress = tourProgress([], TASKS, false);
    expect(Object.values(progress).every((done) => !done)).toBe(true);
    expect(nextStep(progress)).toBe("mistake");
  });

  it("ticks steps from real attempts, in any order", () => {
    const progress = tourProgress([attempt("sql-report", false), attempt("clean-sales", true)], TASKS, false);
    expect(progress).toEqual({ mistake: true, fix: true, sql: true, email: false, skills: false });
    expect(nextStep(progress)).toBe("email");
  });

  it("needs a passed sales file for the fix step and a skills visit to finish", () => {
    const failedOnly = tourProgress([attempt("clean-sales", false)], TASKS, false);
    expect(failedOnly.fix).toBe(false);
    const all = tourProgress(
      [attempt("clean-sales", false), attempt("clean-sales", true), attempt("sql-report", true), attempt("client-email", true)],
      TASKS,
      true,
    );
    expect(nextStep(all)).toBeUndefined();
  });

  it("ignores attempts on unknown task versions", () => {
    const stray = { evaluation: { task_version_id: "other", passed: true } } as Attempt;
    expect(tourProgress([stray], TASKS, false).fix).toBe(false);
  });
});
