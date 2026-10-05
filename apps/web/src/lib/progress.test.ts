import { describe, expect, it } from "vitest";
import type { Attempt } from "./api/contract";
import { evaluation, insightsFor } from "../test/mock-api";
import { previousAttempt, progressDiff, taskHistory } from "./progress";

const attempt = (attempt_number: number, version = "v1", failing: string[] = []) =>
  ({ submission_id: `s${attempt_number}`, attempt_number, evaluation: { ...evaluation(failing), task_version_id: version } }) as Attempt;

describe("attempt history", () => {
  it("keeps one task version, oldest first, and finds the attempt before the current one", () => {
    const history = taskHistory([attempt(3), attempt(1), attempt(1, "v2"), attempt(2)], "v1");
    expect(history.map((item) => item.attempt_number)).toEqual([1, 2, 3]);
    expect(previousAttempt(history, attempt(3))?.attempt_number).toBe(2);
    expect(previousAttempt(history, attempt(1))).toBeUndefined();
  });
});

describe("progressDiff", () => {
  it("names fixed and still-open checks with their issue counts, and the cost recovered", () => {
    const before = evaluation(["unique_orders", "standard_dates"]);
    const after = evaluation(["standard_dates"]);
    const diff = progressDiff(before, after, insightsFor(before), insightsFor(after));

    expect([diff.before, diff.after]).toEqual([50, 75]);
    expect(diff.checks).toEqual([
      { check_id: "unique_orders", status: "fixed", issuesBefore: 2, issuesAfter: 0 },
      { check_id: "standard_dates", status: "open", issuesBefore: 1, issuesAfter: 1 },
    ]);
    expect(diff.metrics.map(({ metric, before: from, after: to }) => [metric.metric_id, from, to])).toEqual([
      ["revenue_overstated", 200, 0],
    ]);
  });

  it("puts a new problem first", () => {
    const diff = progressDiff(evaluation(["standard_dates"]), evaluation(["unique_orders"]), null, null);
    expect(diff.checks.map((change) => [change.check_id, change.status])).toEqual([
      ["unique_orders", "regressed"],
      ["standard_dates", "fixed"],
    ]);
    expect(diff.checks[0].issuesBefore).toBeNull();
  });

  it("treats a rejected previous file as having passed nothing and cost nothing known", () => {
    const rejected = evaluation([], ["missing_columns"]);
    const diff = progressDiff(rejected, evaluation(), insightsFor(rejected), insightsFor(evaluation()));
    expect(diff.previousRejected).toBe(true);
    expect(diff.checks.every((change) => change.status === "fixed")).toBe(true);
    expect(diff.metrics).toEqual([]);
  });
});
