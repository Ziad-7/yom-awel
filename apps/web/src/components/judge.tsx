"use client";
import { useEffect, useState } from "react";
import type { Attempt, SampleInfo, TaskSummary } from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { useLanguage } from "../lib/i18n/language";
import { isSampleId, TOUR_STEPS, type TourStep } from "../lib/i18n/keys";
import { nextStep, tourProgress } from "../lib/tour";

export const SAMPLES_ID = "judge-samples";

/** Judge mode: ready-made submissions that go through the normal upload and grading. */
export function JudgeSamples({ taskId, busy, onSample }: { taskId: string; busy: boolean; onSample: (sample: SampleInfo) => void }) {
  const { t } = useLanguage();
  const [samples, setSamples] = useState<SampleInfo[] | null>(null);

  useEffect(() => {
    let alive = true;
    api.samples(taskId).then(
      (list) => alive && setSamples(list.samples),
      () => alive && setSamples([]),
    );
    return () => {
      alive = false;
    };
  }, [taskId]);

  if (samples !== null && samples.length === 0) return null;
  const copy = t.judge;
  return (
    <section className="card judge-card" id={SAMPLES_ID} aria-labelledby="judge-title" aria-busy={samples === null}>
      <div className="judge-head">
        <span className="judge-badge">{copy.badge}</span>
        <h2 id="judge-title" tabIndex={-1}>
          {copy.title}
        </h2>
      </div>
      <p className="insights-lead">{copy.lead}</p>
      {samples === null ? (
        <p role="status">{copy.loading}</p>
      ) : (
        <ul className="sample-grid">
          {samples.map((sample) => {
            const text = isSampleId(sample.sample_id) ? copy.samples[sample.sample_id] : { title: sample.filename, note: "" };
            return (
              <li key={sample.sample_id}>
                <button type="button" className={`sample-button ${sample.outcome}`} disabled={busy} onClick={() => onSample(sample)}>
                  <span className={`outcome ${sample.outcome}`}>{copy.outcome[sample.outcome](sample.score)}</span>
                  <strong>{text.title}</strong>
                  {text.note && <small>{text.note}</small>}
                  <bdi className="sample-file">{sample.filename}</bdi>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

type TourProps = {
  attempts: Attempt[];
  tasks: TaskSummary[];
  sawSkills: boolean;
  busy: boolean;
  onGo: (step: TourStep) => void;
};

/** A five-step guided tour for judges that ticks itself off from real graded attempts. */
export function JudgeTour({ attempts, tasks, sawSkills, busy, onGo }: TourProps) {
  const { t } = useLanguage();
  const copy = t.judge.tour;
  const progress = tourProgress(attempts, tasks, sawSkills);
  const current = nextStep(progress);
  const done = TOUR_STEPS.filter((step) => progress[step]).length;

  return (
    <section className="card judge-tour" aria-labelledby="tour-title">
      <div className="judge-head">
        <span className="judge-badge">{t.judge.badge}</span>
        <h2 id="tour-title">{copy.title}</h2>
      </div>
      <p className="insights-lead">{current ? copy.lead : copy.complete}</p>
      <p className="tour-progress">
        <label htmlFor="tour-meter">{copy.progress(done, TOUR_STEPS.length)}</label>
        <progress id="tour-meter" max={TOUR_STEPS.length} value={done} />
      </p>
      <ol className="timeline tour-steps">
        {TOUR_STEPS.map((step, index) => {
          const finished = progress[step];
          const active = step === current;
          return (
            <li key={step} className={finished ? "done" : active ? "current" : ""} aria-current={active ? "step" : undefined}>
              <b aria-hidden="true">{finished ? "✓" : index + 1}</b>
              <div>
                {copy.steps[step].title}
                <span className="visually-hidden">: {finished ? copy.done : active ? copy.current : ""}</span>
                {!finished && <small>{copy.steps[step].hint}</small>}
                {active && (
                  <button type="button" className="secondary compact" disabled={busy} onClick={() => onGo(step)}>
                    {copy.go}
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
