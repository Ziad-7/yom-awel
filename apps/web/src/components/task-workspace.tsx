import { useRef } from "react";
import type { GradedAttempt, TaskDetail } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";
import type { Busy } from "../lib/use-workplace";
import { ProcessingState } from "./processing-state";
import { ResultPanel } from "./result-panel";
import { CheckList, DatasetDownloads, TaskBrief } from "./task-brief";
import { UploadForm } from "./upload-form";

const PROCESSING: ReadonlySet<Busy> = new Set(["uploading", "evaluating", "checking"]);

type TaskWorkspaceProps = {
  task: TaskDetail;
  result: GradedAttempt | null;
  completed: boolean;
  attemptNumber: number;
  busy: Busy;
  pending: boolean;
  onSubmit: (file: File) => void;
  onCheck: () => void;
  onSkills: () => void;
  onBack: () => void;
};

function JourneyCard({ completed }: { completed: boolean }) {
  const { t } = useLanguage();
  return (
    <section className="card journey-card" aria-labelledby="journey-title">
      <h2 id="journey-title">{t.journey.title}</h2>
      <ol className="timeline">
        {t.journey.steps.map((step, index) => {
          const done = index === 0 || completed;
          return (
            <li key={step.title} className={done ? "done" : index === 1 ? "current" : ""}>
              <b aria-hidden="true">{done ? "✓" : index + 1}</b>
              <div>
                {step.title}
                <small>{step.hint}</small>
              </div>
            </li>
          );
        })}
      </ol>
      <h3>{t.journey.tipTitle}</h3>
      <p>{t.journey.tip}</p>
    </section>
  );
}

export function TaskWorkspace(props: TaskWorkspaceProps) {
  const { t } = useLanguage();
  const uploadInput = useRef<HTMLInputElement>(null);
  const { task, result } = props;
  const criticalIds = new Set(task.checks.filter((check) => check.critical).map((check) => check.check_id));
  const processing = PROCESSING.has(props.busy);

  function revise() {
    uploadInput.current?.scrollIntoView({ block: "center" });
    uploadInput.current?.focus();
  }

  return (
    <div className="work-grid">
      <div className="work-main">
        <button type="button" className="text-button back" onClick={props.onBack}>
          <span aria-hidden="true" className="arrow back-arrow" /> {t.workspace.back}
        </button>
        {processing && <ProcessingState message={t.status[props.busy as keyof typeof t.status]} />}
        {!processing && result && (
          <ResultPanel
            attempt={result}
            taskId={task.task_id}
            passThreshold={task.pass_threshold}
            criticalIds={criticalIds}
            canRevise={!props.completed}
            onRevise={revise}
            onSkills={props.onSkills}
          />
        )}
        <TaskBrief task={task} />
        <DatasetDownloads task={task} />
        {props.completed ? (
          <section className="card submission-card">
            <p>{t.upload.completed}</p>
          </section>
        ) : (
          <UploadForm
            taskId={task.task_id}
            submissionFormats={task.submission_formats}
            maxBytes={task.max_bytes}
            attemptNumber={props.attemptNumber}
            busy={props.busy !== ""}
            pending={props.pending}
            inputRef={uploadInput}
            onSubmit={props.onSubmit}
            onCheck={props.onCheck}
          />
        )}
      </div>
      <aside className="context-column">
        <CheckList task={task} />
        <JourneyCard completed={props.completed} />
      </aside>
    </div>
  );
}
