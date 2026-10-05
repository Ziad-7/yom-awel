import { API_BASE, request, send } from "./client";
import type {
  Attempt,
  Certificate,
  CoachAnswer,
  CurrentTask,
  DatasetFormat,
  FeedbackResult,
  Learner,
  ProcessingState,
  Runtime,
  SampleInfo,
  SampleList,
  SkillsProfile,
  SubmissionInput,
  SubmissionInsights,
  SubmissionOutcome,
  TaskDetail,
  TaskList,
} from "./contract";
import type { ApiLanguage } from "../i18n/keys";
import { contentTypeOf } from "../uploads";

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
  insights: (submissionId: string) =>
    request<SubmissionInsights>(`/submissions/${encodeURIComponent(submissionId)}/insights`),
  /** Ask Tarek about one's own graded submission; answers come from its facts only. */
  ask: (submissionId: string, question: string, language: ApiLanguage) =>
    request<CoachAnswer>(`/submissions/${encodeURIComponent(submissionId)}/questions`, json("POST", { question, language })),
  myCertificate: () => request<Certificate>("/learners/me/certificate"),
  /** Public: verifies a shared certificate link; needs no session. */
  certificate: (token: string) => request<Certificate>("/certificates/" + encodeURIComponent(token)),
  samples: (taskId: string) => request<SampleList>(task(taskId) + "/samples"),
  /** A judge-mode sample as a File, so it takes exactly the path of a learner's own upload. */
  sampleFile: async (taskId: string, sample: SampleInfo) => {
    const response = await send(`${task(taskId)}/samples/${encodeURIComponent(sample.sample_id)}`);
    return new File([await response.blob()], sample.filename, { type: contentTypeOf(sample.filename) });
  },
};

/** Same-origin link to the dirty learner file; the session cookie authorises the download. */
export const datasetHref = (taskId: string, format: DatasetFormat) =>
  `${API_BASE}${task(taskId)}/dataset?format=${format}`;

export const isOutcome = (
  result: SubmissionOutcome | ProcessingState,
): result is SubmissionOutcome => "evaluation" in result;
