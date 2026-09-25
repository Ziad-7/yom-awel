import type { components } from "./generated";

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

export type Runtime = Schema["RuntimeResult"];
export type TaskSummary = Schema["TaskSummary"];
export type TaskList = Schema["TaskList"];
export type TaskCheck = Schema["CheckInfo"];
export type TaskDetail = Schema["TaskDetail"];
export type LanguageInput = Schema["LanguageInput"];
export type DatasetFormat = "csv" | "xlsx";

/** The part of a graded submission every result view needs. */
export type GradedAttempt = Pick<
  Attempt,
  "submission_id" | "attempt_number" | "evaluation" | "feedback"
>;
