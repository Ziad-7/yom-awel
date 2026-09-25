import { useEffect, useRef } from "react";
import type { EvaluationResult, GradedAttempt } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";
import { isCheckId } from "../lib/i18n/keys";
import { rejectionMessage } from "../lib/messages";
import { FeedbackCard } from "./feedback-card";

type ResultPanelProps = {
  attempt: GradedAttempt;
  passThreshold: number;
  criticalIds: ReadonlySet<string>;
  canRevise: boolean;
  onRevise: () => void;
  onSkills: () => void;
};

export type Verdict = "passed" | "rejected" | "critical_failed" | "failed";

/** Explains why a result is what it is; the evaluator stays the only source of pass/fail. */
export function verdictOf(
  evaluation: EvaluationResult,
  passThreshold: number,
  criticalIds: ReadonlySet<string>,
): Verdict {
  if (evaluation.passed) return "passed";
  if (evaluation.errors.length > 0) return "rejected";
  const criticalFailed = evaluation.checks.some((check) => criticalIds.has(check.check_id) && !check.passed);
  return criticalFailed && evaluation.score >= passThreshold ? "critical_failed" : "failed";
}

function CheckRows({ evaluation }: { evaluation: EvaluationResult }) {
  const { lang, t } = useLanguage();
  return (
    <ul className="result-checks" aria-label={t.result.checksTitle}>
      {evaluation.checks.map((check) => (
        <li key={check.check_id} className={check.passed ? "passed" : "failed"}>
          <span className={check.passed ? "pass-icon" : "fail-icon"}>
            <span aria-hidden="true">{check.passed ? "✓" : "!"}</span> {check.passed ? t.result.passed : t.result.failed}
          </span>
          <div>
            <strong>{isCheckId(check.check_id) ? t.checks[check.check_id].title : check.check_id}</strong>
            <p>{lang === "ar" ? check.details_ar : check.details_en}</p>
          </div>
          <bdi className="points">{t.result.earned(check.passed ? check.weight : 0, check.weight)}</bdi>
        </li>
      ))}
    </ul>
  );
}

export function ResultPanel({ attempt, passThreshold, criticalIds, canRevise, onRevise, onSkills }: ResultPanelProps) {
  const { t } = useLanguage();
  const heading = useRef<HTMLHeadingElement>(null);
  const { evaluation } = attempt;
  const verdict = verdictOf(evaluation, passThreshold, criticalIds);
  useEffect(() => heading.current?.focus(), [attempt.submission_id]);
  const title = {
    passed: t.result.passTitle,
    rejected: t.result.rejectedTitle,
    critical_failed: t.result.failTitle,
    failed: t.result.failTitle,
  }[verdict];

  return (
    <>
      <section className={`card result-card ${verdict}`} aria-labelledby="result-heading">
        <div className="section-heading">
          <h2 id="result-heading" tabIndex={-1} ref={heading}>
            {title}
          </h2>
          <strong className="score" aria-label={`${t.result.score}: ${evaluation.score}/100`}>
            <bdi>{evaluation.score}</bdi>
            <small>/100</small>
          </strong>
        </div>
        <div className={verdict === "passed" ? "banner success" : "banner retry"}>
          {verdict === "passed" && <p>{t.result.success(evaluation.score)}</p>}
          {verdict === "rejected" &&
            evaluation.errors.map((error) => <p key={error.code}>{rejectionMessage(t, error.code)}</p>)}
          {verdict === "critical_failed" && <p>{t.result.criticalFailed(evaluation.score, passThreshold)}</p>}
          {verdict === "failed" && <p>{t.result.failure(evaluation.score)}</p>}
          {verdict !== "passed" && canRevise && <p>{t.result.retry}</p>}
        </div>
        {verdict !== "rejected" && <CheckRows evaluation={evaluation} />}
        <div className="result-actions">
          {verdict === "passed" ? (
            <button type="button" className="primary" onClick={onSkills}>
              {t.result.viewSkills} <span aria-hidden="true" className="arrow" />
            </button>
          ) : canRevise ? (
            <button type="button" className="primary" onClick={onRevise}>
              {t.result.uploadRevision} <span aria-hidden="true">↑</span>
            </button>
          ) : null}
        </div>
      </section>
      <FeedbackCard key={attempt.submission_id} submissionId={attempt.submission_id} initial={attempt.feedback} />
    </>
  );
}
