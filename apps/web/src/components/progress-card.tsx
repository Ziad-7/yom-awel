"use client";
import { useEffect, useState } from "react";
import type { Attempt, GradedAttempt, SubmissionInsights } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";
import { directionOf, isCheckId, isMetricId } from "../lib/i18n/keys";
import { formatMetric } from "../lib/insights";
import { cachedInsights, previousAttempt, progressDiff } from "../lib/progress";

const WIDTH = 320;
const HEIGHT = 120;
// The right margin holds the pass-mark label, clear of every point.
const PAD = { top: 22, right: 78, bottom: 14, left: 14 };

/** One series (this learner's score per attempt) against the pass mark; no legend needed. */
function ScoreChart({ history, threshold }: { history: Attempt[]; threshold: number }) {
  const { t } = useLanguage();
  const copy = t.progress;
  const [active, setActive] = useState<number | null>(null);
  const step = history.length > 1 ? (WIDTH - PAD.left - PAD.right) / (history.length - 1) : 0;
  const x = (index: number) => PAD.left + index * step;
  const y = (score: number) => PAD.top + ((100 - score) / 100) * (HEIGHT - PAD.top - PAD.bottom);
  const labelled = (index: number) => history.length <= 6 || index === 0 || index === history.length - 1;
  const shown = active === null ? null : history[active];

  return (
    <figure className="score-chart">
      <figcaption>{copy.chart}</figcaption>
      <div className="score-chart-frame" dir="ltr">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="group" aria-label={copy.chart}>
          <line className="pass-line" x1={PAD.left} x2={WIDTH - PAD.right} y1={y(threshold)} y2={y(threshold)} />
          <text className="pass-label" x={WIDTH - PAD.right + 8} y={y(threshold) + 4} textAnchor="start">
            {copy.passMark(threshold)}
          </text>
          <polyline className="score-line" points={history.map((attempt, index) => `${x(index)},${y(attempt.evaluation.score)}`).join(" ")} />
          {history.map((attempt, index) => (
            <g
              key={attempt.attempt_number}
              className={`score-point${attempt.evaluation.passed ? " passed" : ""}`}
              tabIndex={0}
              role="img"
              aria-label={copy.point(attempt.attempt_number, attempt.evaluation.score, attempt.evaluation.passed)}
              onMouseEnter={() => setActive(index)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(index)}
              onBlur={() => setActive(null)}
            >
              <circle className="hit" cx={x(index)} cy={y(attempt.evaluation.score)} r={14} />
              <circle className="dot" cx={x(index)} cy={y(attempt.evaluation.score)} r={5} />
              {labelled(index) && (
                <text x={x(index)} y={y(attempt.evaluation.score) - 10} textAnchor="middle">
                  {attempt.evaluation.score}
                </text>
              )}
            </g>
          ))}
        </svg>
        {shown && active !== null && (
          <div className="chart-tooltip" style={{ left: `${(x(active) / WIDTH) * 100}%`, top: `${(y(shown.evaluation.score) / HEIGHT) * 100}%` }} aria-hidden="true">
            {copy.point(shown.attempt_number, shown.evaluation.score, shown.evaluation.passed)}
          </div>
        )}
      </div>
      <table className="visually-hidden">
        <caption>{copy.chart}</caption>
        <thead>
          <tr>
            <th scope="col">{copy.attempt}</th>
            <th scope="col">{copy.score}</th>
            <th scope="col">{copy.result}</th>
          </tr>
        </thead>
        <tbody>
          {history.map((attempt) => (
            <tr key={attempt.attempt_number}>
              <th scope="row">{attempt.attempt_number}</th>
              <td>{attempt.evaluation.score}</td>
              <td>{attempt.evaluation.passed ? copy.passed : copy.notPassed}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

type Loaded = { previous: SubmissionInsights | null; current: SubmissionInsights | null };

/** What changed since the learner's previous attempt at this task: score, checks and cost. */
export function ProgressCard({ current, history, threshold }: { current: GradedAttempt; history: Attempt[]; threshold: number }) {
  const { lang, t } = useLanguage();
  const previous = previousAttempt(history, current);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const previousId = previous?.submission_id;

  useEffect(() => {
    if (!previousId) return;
    let alive = true;
    const settle = (id: string) => cachedInsights(id).catch(() => null);
    Promise.all([settle(previousId), settle(current.submission_id)]).then(([before, after]) => {
      if (alive) setLoaded({ previous: before, current: after });
    });
    return () => {
      alive = false;
    };
  }, [previousId, current.submission_id]);

  if (!previous || current.evaluation.errors.length > 0) return null;
  const copy = t.progress;
  const diff = progressDiff(previous.evaluation, current.evaluation, loaded?.previous ?? null, loaded?.current ?? null);
  const delta = diff.after - diff.before;
  const shown = history.filter((attempt) => attempt.attempt_number <= current.attempt_number);
  const title = (id: string) => (isCheckId(id) ? t.checks[id].title : id);

  return (
    <section className="card progress-card" aria-labelledby="progress-title" aria-busy={loaded === null}>
      <h2 id="progress-title">{copy.title(previous.attempt_number)}</h2>
      <p className={`progress-headline ${delta > 0 ? "up" : delta < 0 ? "down" : "same"}`}>
        <strong>{delta > 0 ? copy.up(delta) : delta < 0 ? copy.down(delta) : copy.same}</strong>
        <span dir={directionOf(lang)}>{copy.change(diff.before, diff.after)}</span>
      </p>
      {diff.previousRejected && <p className="progress-note">{copy.wasRejected}</p>}
      {diff.checks.length > 0 && (
        <ul className="progress-changes">
          {diff.checks.map((change) => (
            <li key={change.check_id} className={change.status}>
              <span className="change-status">{copy.status[change.status]}</span>
              <strong>{title(change.check_id)}</strong>
              {change.issuesBefore !== null && change.issuesAfter !== null && (
                <span className="change-count" dir={directionOf(lang)}>
                  {copy.issues(change.issuesBefore, change.issuesAfter)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {diff.metrics.length > 0 && (
        <>
          <h3>{copy.cost}</h3>
          <ul className="progress-metrics">
            {diff.metrics.map(({ metric, before, after }) =>
              isMetricId(metric.metric_id) ? (
                <li key={metric.metric_id} className={after < before ? "better" : "worse"}>
                  <span>{t.insights.metrics[metric.metric_id].label}</span>
                  <span dir={directionOf(lang)}>
                    {copy.change(formatMetric({ ...metric, value: String(before) }, lang), formatMetric(metric, lang))}
                  </span>
                </li>
              ) : null,
            )}
          </ul>
        </>
      )}
      {shown.length > 1 && <ScoreChart history={shown} threshold={threshold} />}
    </section>
  );
}
