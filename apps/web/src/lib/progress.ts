import type { Attempt, EvaluationResult, GradedAttempt, ImpactMetric, SubmissionInsights } from "./api/contract";
import { api } from "./api/endpoints";

/** A learner's graded attempts at one task version, oldest first. */
export const taskHistory = (attempts: Attempt[], taskVersionId: string) =>
  attempts
    .filter((attempt) => attempt.evaluation.task_version_id === taskVersionId)
    .sort((a, b) => a.attempt_number - b.attempt_number);

export function previousAttempt(history: Attempt[], current: GradedAttempt): Attempt | undefined {
  return history
    .filter((attempt) => attempt.attempt_number < current.attempt_number)
    .reduce<Attempt | undefined>((latest, attempt) => (!latest || attempt.attempt_number > latest.attempt_number ? attempt : latest), undefined);
}

const cache = new Map<string, Promise<SubmissionInsights>>();

/** Insights never change once a submission is graded, so each is fetched once; failures are retried. */
export function cachedInsights(submissionId: string): Promise<SubmissionInsights> {
  let pending = cache.get(submissionId);
  if (!pending) {
    pending = api.insights(submissionId);
    cache.set(submissionId, pending);
    pending.catch(() => cache.delete(submissionId));
  }
  return pending;
}

export type CheckChange = {
  check_id: string;
  status: "fixed" | "regressed" | "open";
  issuesBefore: number | null;
  issuesAfter: number | null;
};
export type MetricChange = { metric: ImpactMetric; before: number; after: number };
export type ProgressDiff = {
  before: number;
  after: number;
  previousRejected: boolean;
  checks: CheckChange[];
  metrics: MetricChange[];
};

const issueCounts = (insights: SubmissionInsights | null) =>
  new Map((insights?.rejected_code ? [] : (insights?.checks ?? [])).map((check) => [check.check_id, check.issue_count]));

/** What changed between two graded attempts, from the evaluator's own checks and insights. */
export function progressDiff(
  previous: EvaluationResult,
  current: EvaluationResult,
  previousInsights: SubmissionInsights | null,
  currentInsights: SubmissionInsights | null,
): ProgressDiff {
  const previousRejected = previous.errors.length > 0;
  const passedBefore = new Map(previous.checks.map((check) => [check.check_id, check.passed && !previousRejected]));
  const issuesBefore = issueCounts(previousInsights);
  const issuesAfter = issueCounts(currentInsights);
  const checks = current.checks.flatMap((check): CheckChange[] => {
    const before = passedBefore.get(check.check_id) ?? false;
    if (before && check.passed) return [];
    const status = check.passed ? "fixed" : before ? "regressed" : "open";
    return [{ check_id: check.check_id, status, issuesBefore: issuesBefore.get(check.check_id) ?? null, issuesAfter: issuesAfter.get(check.check_id) ?? null }];
  });
  const order = { regressed: 0, fixed: 1, open: 2 };
  checks.sort((a, b) => order[a.status] - order[b.status]);
  const beforeMetrics = new Map((previousRejected ? [] : (previousInsights?.impact ?? [])).map((metric) => [metric.metric_id, Number(metric.value)]));
  const metrics = (currentInsights?.impact ?? []).flatMap((metric) => {
    const before = beforeMetrics.get(metric.metric_id);
    const after = Number(metric.value);
    return before === undefined || before === after ? [] : [{ metric, before, after }];
  });
  return { before: previous.score, after: current.score, previousRejected, checks, metrics };
}

/** Tests reuse submission ids across mocked APIs. */
export const clearInsightsCache = () => cache.clear();
