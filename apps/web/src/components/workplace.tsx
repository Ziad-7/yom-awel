"use client";
import { useLanguage } from "../lib/i18n/language";
import { errorMessage } from "../lib/messages";
import { isStillProcessing, useWorkplace, type View } from "../lib/use-workplace";
import { useState } from "react";
import { AppShell, PageHeading } from "./app-shell";
import { ErrorBanner } from "./error-banner";
import { Onboarding } from "./onboarding";
import { RestartDialog } from "./restart-dialog";
import { SkillsProgress } from "./skills-progress";
import { TaskCatalogue } from "./task-catalogue";
import { TaskWorkspace } from "./task-workspace";

export default function Workplace({ initialView = "tasks" }: { initialView?: View }) {
  const { lang, t } = useLanguage();
  const { state, actions } = useWorkplace(initialView);
  const [restartOpen, setRestartOpen] = useState(false);
  const { learner, detail, view, busy } = state;
  const active = detail ? state.tasks.find((task) => task.task_id === detail.task_id) : undefined;
  const completed = active?.status === "completed";
  const failure = isStillProcessing(state.failure) ? t.errors.stillProcessing : errorMessage(t, state.failure);
  const title = !learner
    ? t.headings.welcome
    : view === "skills"
      ? t.headings.skills
      : view === "work" && detail
        ? lang === "ar"
          ? detail.title_ar
          : detail.title_en
        : t.headings.greeting(learner.display_name);

  function body() {
    if (!learner)
      return (
        <Onboarding
          disabled={busy !== "" || state.booting || !state.runtime}
          onLanguage={actions.changeLanguage}
          onSubmit={(name) => actions.join(name, lang)}
        />
      );
    if (view === "skills")
      return (
        <SkillsProgress
          skills={state.skills}
          attempts={state.attempts}
          tasks={state.tasks}
          canRetry={!!detail && !completed}
          onRetry={() => actions.setView("work")}
          onWork={() => actions.setView(detail ? "work" : "tasks")}
          onViewAttempt={actions.viewAttempt}
        />
      );
    if (view === "work" && detail)
      return (
        <TaskWorkspace
          task={detail}
          result={state.result}
          completed={completed}
          attemptNumber={state.attempts.filter((attempt) => attempt.evaluation.task_version_id === detail.task_version_id).length + 1}
          busy={busy}
          pending={state.pending?.body.task_version_id === detail.task_version_id}
          onSubmit={actions.submit}
          onCheck={actions.checkPending}
          onSkills={() => actions.setView("skills")}
          onBack={() => actions.setView("tasks")}
        />
      );
    return <TaskCatalogue tasks={state.tasks} disabled={busy !== ""} onOpen={actions.openTask} />;
  }

  return (
    <AppShell
      view={view}
      learner={learner}
      runtime={state.runtime}
      canWork={!!detail}
      languageBusy={busy === "savingLanguage"}
      onNavigate={actions.setView}
      onLanguage={actions.changeLanguage}
      onRestart={() => setRestartOpen(true)}
    >
      <main id="main">
        <PageHeading title={title} />
        {state.failure !== null && <ErrorBanner message={failure} onDismiss={actions.dismiss} />}
        <div role="status" aria-live="polite" className="loading-status">
          {busy ? t.status[busy] : state.booting ? t.status.booting : ""}
        </div>
        {!state.booting && !state.runtime && (
          <button type="button" className="secondary" onClick={() => location.reload()}>
            {t.errors.retry}
          </button>
        )}
        {!state.booting && body()}
        <footer>{t.shell.footer}</footer>
      </main>
      {restartOpen && (
        <RestartDialog
          onCancel={() => setRestartOpen(false)}
          onConfirm={() => {
            setRestartOpen(false);
            void actions.restart();
          }}
        />
      )}
    </AppShell>
  );
}
