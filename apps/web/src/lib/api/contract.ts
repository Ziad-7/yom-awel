import type { components } from "./generated";
import type { ApiLanguage, TaskStatus } from "../i18n/keys";

type Schema = components["schemas"];

export type Learner = Schema["Learner"];
export type SkillsProfile = Schema["SkillsProfile"];
export type Attempt = Schema["AttemptResult"];
export type EvaluationResult = Schema["EvaluationResult"];
export type FeedbackResult = Schema["FeedbackResult"];
export type SubmissionInput = Schema["SubmissionInput"];
export type SubmissionOutcome = Schema["SubmissionOutcome"];
export type ProcessingState = Schema["ProcessingState"];
export type UploadAuthorization = Schema["UploadAuthorizationResult"];
export type UploadCompletion = Schema["UploadCompletionResult"];
export type CurrentTask = Schema["CurrentTaskResult"];

export type Runtime = {
  mode: "local" | "cloud";
  feedback_provider: "gemini" | "deterministic";
};
export type TaskSummary = {
  task_id: string;
  version: string;
  task_version_id: string;
  title_ar: string;
  title_en: string;
  status: TaskStatus;
  pass_threshold: number;
  points_total: number;
};
export type TaskList = { tasks: TaskSummary[] };
export type TaskCheck = { check_id: string; points: number; critical: boolean };
export type TaskDetail = {
  task_id: string;
  version: string;
  task_version_id: string;
  title_ar: string;
  title_en: string;
  brief_ar: string;
  brief_en: string;
  hints_ar: string;
  hints_en: string;
  pass_threshold: number;
  formats: ("csv" | "xlsx")[];
  max_bytes: number;
  checks: TaskCheck[];
};
export type LanguageInput = { preferred_language: ApiLanguage };
export type DatasetFormat = "csv" | "xlsx";

/** The part of a graded submission every result view needs. */
export type GradedAttempt = Pick<
  Attempt,
  "submission_id" | "attempt_number" | "evaluation" | "feedback"
>;
