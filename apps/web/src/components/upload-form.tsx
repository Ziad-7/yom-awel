import { useRef, useState } from "react";
import { useLanguage } from "../lib/i18n/language";
import { rejectionMessage } from "../lib/messages";
import { inspectFile } from "../lib/uploads";
import type { TaskDetail } from "../lib/api/contract";

type UploadFormProps = {
  taskId: string;
  submissionFormats: TaskDetail["submission_formats"];
  maxBytes: number;
  attemptNumber: number;
  busy: boolean;
  pending: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onSubmit: (file: File) => void;
  onCheck: () => void;
};

export function UploadForm({ inputRef, ...props }: UploadFormProps) {
  const { t } = useLanguage();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState("");
  const selection = useRef(0);
  const textTask = props.taskId === "sql-report" || props.taskId === "client-email";
  const extension = props.taskId === "sql-report" ? ".sql" : props.taskId === "client-email" ? ".txt" : "";
  const accepted = textTask ? extension : ".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const formatLabel = props.taskId === "sql-report" ? t.upload.sqlFormats : props.taskId === "client-email" ? t.upload.emailFormats : t.upload.formats(Math.round(props.maxBytes / 1024 / 1024));

  async function choose(next: File | undefined) {
    const current = ++selection.current;
    setFile(null);
    setError("");
    if (!next) return;
    const chosenExtension = next.name.toLowerCase().split(".").pop();
    if (!chosenExtension || !props.submissionFormats.includes(chosenExtension as TaskDetail["submission_formats"][number])) {
      setError(textTask ? formatLabel : t.rejections.unsupported_type);
      return;
    }
    const invalid = await inspectFile(next, props.maxBytes);
    if (current !== selection.current) return;
    if (invalid) setError(rejectionMessage(t, invalid));
    else {
      setAnswer("");
      setFile(next);
    }
  }
  function chooseAnother() {
    if (inputRef.current) inputRef.current.value = "";
    void choose(undefined);
    inputRef.current?.click();
  }

  function submit() {
    if (props.pending) {
      props.onCheck();
      return;
    }
    if (file) {
      props.onSubmit(file);
      return;
    }
    if (!textTask || !answer.trim()) {
      setError(t.upload.emptyEditor);
      return;
    }
    const draft = new File([answer], `submission${extension}`, { type: "text/plain" });
    if (draft.size > props.maxBytes) {
      setError(t.rejections.artifact_too_large);
      return;
    }
    props.onSubmit(draft);
  }

  return (
    <section className="card submission-card" aria-labelledby="upload-title">
      <div className="section-heading">
        <h2 id="upload-title">{t.upload.title}</h2>
        <span className="muted">{t.upload.attempt(props.attemptNumber)}</span>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        {textTask && (
          <div className="answer-editor">
            <label htmlFor="submission-answer">
              {props.taskId === "sql-report" ? t.upload.sqlEditor : t.upload.emailEditor}
            </label>
            <p className="muted">{t.upload.editorHint}</p>
            <textarea
              id="submission-answer"
              value={answer}
              rows={12}
              spellCheck={props.taskId === "client-email"}
              dir={props.taskId === "sql-report" ? "ltr" : undefined}
              disabled={props.busy || props.pending}
              onChange={(event) => {
                setAnswer(event.target.value);
                setFile(null);
                setError("");
                if (inputRef.current) inputRef.current.value = "";
              }}
            />
          </div>
        )}
        <label className="upload-zone" htmlFor="submission">
          <span className="upload-icon" aria-hidden="true">
            ↑
          </span>
          <strong>{file ? <bdi>{file.name}</bdi> : t.upload.choose}</strong>
          <span>{formatLabel}</span>
          <input
            ref={inputRef}
            id="submission"
            type="file"
            accept={accepted}
            disabled={props.busy || props.pending}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "upload-error" : undefined}
            onChange={(event) => void choose(event.target.files?.[0])}
          />
        </label>
        {error && (
          <div className="inline-error" id="upload-error" role="alert">
            <span>{error}</span>
            <button type="button" className="text-button" onClick={chooseAnother}>
              {t.upload.another}
            </button>
          </div>
        )}
        <div className="submission-actions">
          <p>{t.upload.encouragement}</p>
          <button className="primary" disabled={props.busy || (!file && !answer.trim() && !props.pending)}>
            {props.pending ? t.upload.check : t.upload.submit} <span aria-hidden="true" className="arrow" />
          </button>
        </div>
      </form>
    </section>
  );
}
