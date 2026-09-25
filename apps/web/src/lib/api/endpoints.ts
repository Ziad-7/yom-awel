import { API_BASE, request, send } from "./client";
import type {
  Attempt,
  CurrentTask,
  DatasetFormat,
  FeedbackResult,
  Learner,
  ProcessingState,
  Runtime,
  SkillsProfile,
  SubmissionInput,
  SubmissionOutcome,
  TaskDetail,
  TaskList,
} from "./contract";
import type { ApiLanguage } from "../i18n/keys";

const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
const task = (taskId: string) => "/tasks/" + encodeURIComponent(taskId);

export const api = {
  runtime: () => request<Runtime>("/runtime"),
  createSession: () => send("/auth/session", { method: "POST" }).then(() => undefined),
  logout: () => send("/auth/logout", { method: "POST" }).then(() => undefined),
  me: () => request<Learner>("/learners/me"),
  onboard: (display_name: string, preferred_language: ApiLanguage) =>
    request<Learner>("/learners/onboard", json("POST", { display_name, preferred_language })),
  setLanguage: (preferred_language: ApiLanguage) =>
    request<Learner>("/learners/me/language", json("PUT", { preferred_language })),
  tasks: () => request<TaskList>("/tasks"),
  task: (taskId: string) => request<TaskDetail>(task(taskId)),
  startTask: (taskId: string) =>
    request<CurrentTask>(task(taskId) + "/start", { method: "POST" }),
  skills: () => request<SkillsProfile>("/skills"),
  attempts: () => request<Attempt[]>("/attempts"),
  submit: (body: SubmissionInput, idempotencyKey: string) =>
    request<SubmissionOutcome | ProcessingState>("/submissions", {
      ...json("POST", body),
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  submission: (submissionId: string, idempotencyKey: string) =>
    request<SubmissionOutcome | ProcessingState>(
      "/submissions/" + encodeURIComponent(submissionId),
      { headers: { "Idempotency-Key": idempotencyKey } },
    ),
  feedback: (submissionId: string, language: ApiLanguage) =>
    request<FeedbackResult>(
      `/submissions/${encodeURIComponent(submissionId)}/feedback?language=${language}`,
    ),
};

/** Same-origin link to the dirty learner file; the session cookie authorises the download. */
export const datasetHref = (taskId: string, format: DatasetFormat) =>
  `${API_BASE}${task(taskId)}/dataset?format=${format}`;

export const isOutcome = (
  result: SubmissionOutcome | ProcessingState,
): result is SubmissionOutcome => "evaluation" in result;
