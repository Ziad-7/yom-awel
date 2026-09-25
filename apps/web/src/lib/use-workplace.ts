"use client";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api/client";
import type {
  Attempt,
  GradedAttempt,
  Learner,
  ProcessingState,
  Runtime,
  SkillsProfile,
  SubmissionInput,
  SubmissionOutcome,
  TaskDetail,
  TaskSummary,
} from "./api/contract";
import { api, isOutcome } from "./api/endpoints";
import type { Dictionary } from "./i18n/en";
import { useLanguage } from "./i18n/language";
import { fromApiLanguage, toApiLanguage, type Lang } from "./i18n/keys";
import { uploadFile } from "./uploads";

export type View = "tasks" | "work" | "skills";
export type Busy = keyof Dictionary["status"] | "";
export type Pending = { key: string; body: SubmissionInput; submissionId?: string };

const PENDING_KEY = "yom-awel.pending";
const MAX_POLLS = 20;
const wait = (seconds: number) => new Promise((resolve) => setTimeout(resolve, Math.min(seconds, 3) * 1000));

class StillProcessing extends Error {}

function readPending(learnerId: string): Pending | null {
  try {
    const saved = JSON.parse(sessionStorage.getItem(PENDING_KEY) ?? "null");
    return saved?.learnerId === learnerId ? (saved.pending as Pending) : null;
  } catch {
    return null;
  }
}
function writePending(learnerId: string, pending: Pending | null) {
  try {
    if (pending) sessionStorage.setItem(PENDING_KEY, JSON.stringify({ learnerId, pending }));
    else sessionStorage.removeItem(PENDING_KEY);
  } catch {
    /* storage can be unavailable; the idempotency key then lives only in memory */
  }
}

/** The task a returning learner should land on: in progress first, then the latest completed. */
export const activeTask = (tasks: TaskSummary[]) =>
  tasks.find((task) => task.status === "in_progress") ?? tasks.find((task) => task.status === "completed");

export const latestAttempt = (attempts: Attempt[]): GradedAttempt | null =>
  attempts.reduce<Attempt | null>(
    (latest, item) => (!latest || item.attempt_number > latest.attempt_number ? item : latest),
    null,
  );

async function awaitOutcome(first: SubmissionOutcome | ProcessingState): Promise<SubmissionOutcome> {
  let result = first;
  for (let poll = 0; !isOutcome(result); poll++) {
    if (poll >= MAX_POLLS) throw new StillProcessing();
    await wait(result.retry_after_seconds);
    result = await api.submission(result.submission_id);
  }
  return result;
}

export function useWorkplace(initialView: View) {
  const { setLang } = useLanguage();
  const [view, setView] = useState<View>(initialView);
  const [booting, setBooting] = useState(true);
  const [busy, setBusy] = useState<Busy>("");
  const [failure, setFailure] = useState<unknown>(null);
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [learner, setLearner] = useState<Learner | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [skills, setSkills] = useState<SkillsProfile | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [result, setResult] = useState<GradedAttempt | null>(null);
  const [pending, setPendingState] = useState<Pending | null>(null);

  const setPending = useCallback(
    (next: Pending | null) => {
      setPendingState(next);
      if (learner) writePending(learner.learner_id, next);
    },
    [learner],
  );

  const reset = useCallback(() => {
    setLearner(null);
    setTasks([]);
    setDetail(null);
    setSkills(null);
    setAttempts([]);
    setResult(null);
    setPendingState(null);
    setView("tasks");
  }, []);

  const report = useCallback(
    (cause: unknown) => {
      if (cause instanceof ApiError && cause.status === 401) reset();
      setFailure(cause);
    },
    [reset],
  );

  const loadProgress = useCallback(async () => {
    const [list, profile, history] = await Promise.all([api.tasks(), api.skills(), api.attempts()]);
    setTasks(list.tasks);
    setSkills(profile);
    setAttempts(history);
    return { tasks: list.tasks, attempts: history };
  }, []);

  useEffect(() => {
    let alive = true;
    async function restore() {
      try {
        const config = await api.runtime();
        if (!alive) return;
        setRuntime(config);
        const me = await api.me().catch((cause: unknown) => {
          if (cause instanceof ApiError && (cause.status === 401 || cause.status === 404)) return null;
          throw cause;
        });
        if (!me || !alive) return;
        setLang(fromApiLanguage(me.preferred_language));
        const progress = await loadProgress();
        const current = activeTask(progress.tasks);
        if (current) {
          const task = await api.task(current.task_id);
          if (!alive) return;
          setDetail(task);
          setResult(latestAttempt(progress.attempts));
        } else if (initialView === "work") setView("tasks");
        setPendingState(readPending(me.learner_id));
        setLearner(me);
      } catch (cause) {
        if (alive) report(cause);
      } finally {
        if (alive) setBooting(false);
      }
    }
    void restore();
    return () => {
      alive = false;
    };
  }, [initialView, loadProgress, report, setLang]);

  async function run(label: Busy, action: () => Promise<void>) {
    setFailure(null);
    setBusy(label);
    try {
      await action();
    } catch (cause) {
      report(cause);
    } finally {
      setBusy("");
    }
  }

  const join = (name: string, lang: Lang) =>
    run("joining", async () => {
      await api.me().catch(async (cause: unknown) => {
        if (cause instanceof ApiError && cause.status === 401) await api.createSession();
        else if (!(cause instanceof ApiError && cause.status === 404)) throw cause;
      });
      const me = await api.onboard(name, toApiLanguage(lang));
      await loadProgress();
      setLearner(me);
      setView("tasks");
    });

  const changeLanguage = (lang: Lang) => {
    setLang(lang);
    if (!learner) return;
    void run("savingLanguage", async () => setLearner(await api.setLanguage(toApiLanguage(lang))));
  };

  const openTask = (task: TaskSummary) =>
    run("starting", async () => {
      if (task.status !== "completed") await api.startTask(task.task_id);
      const [next, progress] = await Promise.all([api.task(task.task_id), loadProgress()]);
      setDetail(next);
      setResult(task.status === "available" ? null : latestAttempt(progress.attempts));
      setView("work");
    });

  async function finish(outcome: SubmissionOutcome) {
    setPending(null);
    setResult(outcome);
    setLearner((current) => (current ? { ...current, status: outcome.learner_status } : current));
    await loadProgress();
  }

  async function evaluate(attempt: Pending) {
    setBusy("evaluating");
    const first = attempt.submissionId
      ? await api.submission(attempt.submissionId)
      : await api.submit(attempt.body, attempt.key);
    if (!isOutcome(first)) setPending({ ...attempt, submissionId: first.submission_id });
    await finish(await awaitOutcome(first));
  }

  const submit = (file: File) =>
    run("uploading", async () => {
      if (!detail) return;
      const artifact = await uploadFile(file);
      const attempt: Pending = {
        key: crypto.randomUUID(),
        body: { ...artifact, task_version_id: detail.task_version_id },
      };
      setPending(attempt);
      setResult(null);
      await evaluate(attempt);
    });

  const checkPending = () =>
    run("checking", async () => {
      if (pending) await evaluate(pending);
    });

  const restart = () =>
    run("joining", async () => {
      await api.createSession();
      writePending("", null);
      reset();
    });

  const viewAttempt = (attempt: GradedAttempt) => {
    setResult(attempt);
    setView("work");
  };

  return {
    state: { view, booting, busy, failure, runtime, learner, tasks, detail, skills, attempts, result, pending },
    actions: {
      setView,
      dismiss: () => setFailure(null),
      join,
      changeLanguage,
      openTask,
      submit,
      checkPending,
      restart,
      viewAttempt,
    },
  };
}

export const isStillProcessing = (cause: unknown) => cause instanceof StillProcessing;
