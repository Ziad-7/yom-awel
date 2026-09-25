import { useRef, useState } from "react";
import { useLanguage } from "../lib/i18n/language";
import { rejectionMessage } from "../lib/messages";
import { inspectFile } from "../lib/uploads";

type UploadFormProps = {
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
  const selection = useRef(0);

  async function choose(next: File | undefined) {
    const current = ++selection.current;
    setFile(null);
    setError("");
    if (!next) return;
    const invalid = await inspectFile(next, props.maxBytes);
    if (current !== selection.current) return;
    if (invalid) setError(rejectionMessage(t, invalid));
    else setFile(next);
  }
  function chooseAnother() {
    if (inputRef.current) inputRef.current.value = "";
    void choose(undefined);
    inputRef.current?.click();
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
          if (props.pending) props.onCheck();
          else if (file) props.onSubmit(file);
        }}
      >
        <label className="upload-zone" htmlFor="submission">
          <span className="upload-icon" aria-hidden="true">
            ↑
          </span>
          <strong>{file ? <bdi>{file.name}</bdi> : t.upload.choose}</strong>
          <span>{t.upload.formats(Math.round(props.maxBytes / 1024 / 1024))}</span>
          <input
            ref={inputRef}
            id="submission"
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
          <button className="primary" disabled={props.busy || (!file && !props.pending)}>
            {props.pending ? t.upload.check : t.upload.submit} <span aria-hidden="true" className="arrow" />
          </button>
        </div>
      </form>
    </section>
  );
}
