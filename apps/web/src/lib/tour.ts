import type { Attempt, TaskSummary } from "./api/contract";
import { TOUR_STEPS, type TourStep } from "./i18n/keys";

/** Where each step of the judge's tour happens: a task's workspace, or the skills page. */
export const TOUR_TARGETS: Record<TourStep, string> = {
  mistake: "clean-sales",
  fix: "clean-sales",
  sql: "sql-report",
  email: "client-email",
  skills: "skills",
};

/** Each step ticks itself off from the learner's real, graded attempts. */
export function tourProgress(attempts: Attempt[], tasks: TaskSummary[], sawSkills: boolean): Record<TourStep, boolean> {
  const taskOf = new Map(tasks.map((task) => [task.task_version_id, task.task_id]));
  const graded = attempts.map((attempt) => ({
    task: taskOf.get(attempt.evaluation.task_version_id),
    passed: attempt.evaluation.passed,
  }));
  return {
    mistake: graded.some((attempt) => !attempt.passed),
    fix: graded.some((attempt) => attempt.task === "clean-sales" && attempt.passed),
    sql: graded.some((attempt) => attempt.task === "sql-report"),
    email: graded.some((attempt) => attempt.task === "client-email"),
    skills: sawSkills,
  };
}

export const nextStep = (progress: Record<TourStep, boolean>): TourStep | undefined =>
  TOUR_STEPS.find((step) => !progress[step]);
