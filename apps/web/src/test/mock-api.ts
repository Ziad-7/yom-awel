import type {
  Attempt,
  EvaluationResult,
  FeedbackResult,
  Learner,
  Runtime,
  SkillsProfile,
  SubmissionOutcome,
  TaskDetail,
  TaskList,
  TaskSummary,
} from "../lib/api/contract";
import type { ApiLanguage } from "../lib/i18n/keys";

/** A typed, in-memory stand-in for the /api/v1 contract used by component tests. */
export type Call = { method: string; path: string; headers: Record<string, string>; body?: unknown };

const TASK_VERSION = "00000000-0000-4000-8000-00000000000a";
const SUBMISSION = "00000000-0000-4000-8000-00000000000b";
const CHECK_IDS = ["unique_orders", "standard_dates", "valid_numeric_values", "complete_customer_records"];

export const detail: TaskDetail = {
  task_id: "clean-sales",
  version: "1",
  task_version_id: TASK_VERSION,
  title_ar: "تنظيف بيانات المبيعات",
  title_en: "Clean the sales data",
  brief_ar: "# التكليف\n\n- **نظّف** الملف `sales_dirty.csv`\n<script>alert(1)</script>",
  brief_en: "# The brief\n\n- **Clean** the file `sales_dirty.csv`\n<script>alert(1)</script>",
  hints_ar: "### تلميح\n- استخدم Remove Duplicates",
  hints_en: "### Hint\n- Use Remove Duplicates",
  pass_threshold: 75,
  formats: ["csv", "xlsx"],
  max_bytes: 5242880,
  checks: CHECK_IDS.map((check_id) => ({ check_id, points: 25, critical: check_id === "unique_orders" })),
};

export function evaluation(failing: string[] = [], errors: string[] = []): EvaluationResult {
  const checks = CHECK_IDS.map((check_id) => {
    const passed = !errors.length && !failing.includes(check_id);
    return {
      check_id,
      passed,
      weight: 25,
      details_ar: passed ? "تمام." : "محتاج تتصلح.",
      details_en: passed ? "All good." : "Needs fixing.",
      diagnostic_code: `${check_id}_${passed ? "passed" : "failed"}`,
    };
  });
  const score = checks.filter((check) => check.passed).length * 25;
  return {
    evaluator_id: "sales-cleaning",
    evaluator_version: "1",
    task_version_id: TASK_VERSION,
    passed: !errors.length && score >= 75 && !failing.includes("unique_orders"),
    score,
    checks,
    errors: errors.map((code) => ({ code, message: code })),
    summary_ar: "",
    summary_en: "",
    duration_ms: 3,
  };
}

export const feedback = (language: ApiLanguage): FeedbackResult => ({
  language,
  feedback_text:
    language === "en"
      ? "Eng. Tarek, Team Lead\nDecision: resubmit.\nNext step: remove duplicates."
      : "م. طارق، مشرف الفريق\nالقرار: أعد التسليم.\nالخطوة الجاية: شيل التكرار.",
  persona_id: "tarek",
  prompt_version: "1",
  provider: "deterministic",
  model: null,
  used_fallback: true,
  duration_ms: 1,
});

export function createMockApi(outcome: EvaluationResult) {
  const calls: Call[] = [];
  let session = false;
  let learner: Learner | null = null;
  let status: TaskSummary["status"] = "available";
  const attempts: Attempt[] = [];
  const runtime: Runtime = { mode: "local", feedback_provider: "deterministic" };
  const tasks = (): TaskList => ({
    tasks: [
      {
        task_id: detail.task_id,
        version: detail.version,
        task_version_id: detail.task_version_id,
        title_ar: detail.title_ar,
        title_en: detail.title_en,
        status,
        pass_threshold: detail.pass_threshold,
        points_total: 100,
      },
    ],
  });
  const skills = (): SkillsProfile => ({
    learner_id: learner?.learner_id ?? "",
    skills: attempts.length ? [{ skill_id: "data_cleaning", score: outcome.score }] : [],
  });

  function route(path: string, body: unknown): [number, unknown] {
    if (path === "/api/v1/runtime") return [200, runtime];
    if (path === "/api/v1/auth/session") return (session = true), [200, {}];
    if (!session) return [401, { code: "unauthorized" }];
    if (path === "/api/v1/learners/onboard") {
      const input = body as { display_name: string; preferred_language: ApiLanguage };
      learner = {
        learner_id: "00000000-0000-4000-8000-000000000001",
        display_name: input.display_name,
        preferred_language: input.preferred_language,
        status: "READY",
        state_machine_version: "1",
        created_at: "2026-09-24T00:00:00Z",
        updated_at: "2026-09-24T00:00:00Z",
      };
      return [200, learner];
    }
    if (!learner) return [404, { code: "learner_not_found" }];
    if (path === "/api/v1/learners/me") return [200, learner];
    if (path === "/api/v1/learners/me/language") {
      learner = { ...learner, ...(body as Pick<Learner, "preferred_language">) };
      return [200, learner];
    }
    if (path === "/api/v1/tasks") return [200, tasks()];
    if (path === "/api/v1/tasks/clean-sales/start") return (status = "in_progress"), [200, { status: "IN_TASK", task: null }];
    if (path === "/api/v1/tasks/clean-sales") return [200, detail];
    if (path === "/api/v1/skills") return [200, skills()];
    if (path === "/api/v1/attempts") return [200, attempts];
    if (path === "/api/v1/artifacts/upload-authorization")
      return [200, { artifact_id: "00000000-0000-4000-8000-00000000000c", upload_url: "/api/v1/artifacts/00000000-0000-4000-8000-00000000000c/content", headers: {}, expires_in_seconds: 300, upload_token: null }];
    if (path.endsWith("/content") || path.endsWith("/complete"))
      return [200, { artifact_id: "00000000-0000-4000-8000-00000000000c" }];
    if (path === "/api/v1/submissions") {
      const result: SubmissionOutcome = {
        submission_id: SUBMISSION,
        attempt_id: SUBMISSION,
        attempt_number: attempts.length + 1,
        evaluation: outcome,
        feedback: feedback(learner.preferred_language),
        learner_status: outcome.passed ? "TASK_COMPLETED" : "NEEDS_RETRY",
        task_status: outcome.passed ? "COMPLETED" : "ACTIVE",
        skills: [],
      };
      attempts.push(result);
      status = outcome.passed ? "completed" : "in_progress";
      return [200, result];
    }
    const language = new URL(path, "http://x").searchParams.get("language") as ApiLanguage | null;
    if (path.startsWith(`/api/v1/submissions/${SUBMISSION}/feedback`) && language) return [200, feedback(language)];
    return [404, { code: "not_found" }];
  }

  const fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = typeof init.body === "string" ? JSON.parse(init.body) : undefined;
    calls.push({ method, path: url, headers: { ...(init.headers as Record<string, string>) }, body });
    if (method !== "GET" && (init.headers as Record<string, string>)["X-Yom-Awel"] !== "1")
      return new Response(JSON.stringify({ code: "csrf" }), { status: 403 });
    const [code, payload] = route(url, body);
    return new Response(JSON.stringify(payload), { status: code, headers: { "Content-Type": "application/json" } });
  };
  return { fetch, calls };
}
