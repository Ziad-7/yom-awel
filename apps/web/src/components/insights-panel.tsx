"use client";
import { useEffect, useMemo, useState } from "react";
import type {
  CellIssue,
  EmailInsight,
  ImpactMetric,
  SqlInsight,
  SubmissionInsights,
  TablePreview,
} from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { useLanguage } from "../lib/i18n/language";
import { isCheckId, isEmailElementId, isIssueCode, isMetricId } from "../lib/i18n/keys";
import { emailSegments, formatMetric, isZero, peersOf, tableXray } from "../lib/insights";

type Load = { status: "loading" } | { status: "error" } | { status: "ready"; insights: SubmissionInsights };
type Check = SubmissionInsights["checks"][number];

function useCheckTitle() {
  const { t } = useLanguage();
  return (checkId: string) => (isCheckId(checkId) ? t.checks[checkId].title : checkId);
}

function ImpactCard({ impact }: { impact: ImpactMetric[] }) {
  const { lang, t } = useLanguage();
  const metrics = impact.filter((metric) => isMetricId(metric.metric_id));
  if (!metrics.length) return null;
  const clear = metrics.every(isZero);
  return (
    <section className={clear ? "card impact-card clear" : "card impact-card"} aria-labelledby="impact-title">
      <h2 id="impact-title">{t.insights.impactTitle}</h2>
      <p className="insights-lead">{clear ? t.insights.impactClear : t.insights.impactLead}</p>
      <ul className="impact-grid">
        {metrics.map((metric) => {
          const id = metric.metric_id;
          if (!isMetricId(id)) return null;
          return (
            <li key={id} className={isZero(metric) ? "zero" : "cost"}>
              <strong>
                <bdi>{formatMetric(metric, lang)}</bdi>
              </strong>
              <span>{t.insights.metrics[id].label}</span>
              <small>{t.insights.metrics[id].hint}</small>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function IssueLabel({ issue }: { issue: CellIssue }) {
  const { t } = useLanguage();
  return <>{isIssueCode(issue.issue) ? t.insights.issues[issue.issue] : issue.issue}</>;
}

function TableView({ table, issues, checks }: { table: TablePreview; issues: CellIssue[]; checks: Check[] }) {
  const { t } = useLanguage();
  const checkTitle = useCheckTitle();
  const [checkId, setCheckId] = useState<string | null>(null);
  const [onlyIssues, setOnlyIssues] = useState(true);
  const xray = useMemo(() => tableXray(table, issues, checkId, onlyIssues), [table, issues, checkId, onlyIssues]);
  const copy = t.insights.table;
  if (!issues.length) return <p className="banner success">{copy.clean}</p>;
  const failing = checks.filter((check) => check.issue_count > 0);

  return (
    <>
      <p className="xray-summary">{copy.summary(issues.length, new Set(issues.map((issue) => issue.row)).size)}</p>
      <div className="xray-controls">
        <div className="xray-filters" role="group" aria-label={copy.filters}>
          <button type="button" className="chip" aria-pressed={checkId === null} onClick={() => setCheckId(null)}>
            {copy.all} <bdi>{issues.length}</bdi>
          </button>
          {failing.map((check) => (
            <button
              key={check.check_id}
              type="button"
              className="chip"
              aria-pressed={checkId === check.check_id}
              onClick={() => setCheckId(check.check_id)}
            >
              {checkTitle(check.check_id)} <bdi>{check.issue_count}</bdi>
            </button>
          ))}
        </div>
        <label className="xray-toggle">
          <input type="checkbox" checked={onlyIssues} onChange={(event) => setOnlyIssues(event.target.checked)} />
          {copy.onlyIssues}
        </label>
      </div>
      <div className="xray-scroll" role="region" aria-label={copy.region} tabIndex={0}>
        <table className="xray-table">
          <caption className="visually-hidden">{copy.caption}</caption>
          <thead>
            <tr>
              <th scope="col">{copy.row}</th>
              <th scope="col">{copy.problems}</th>
              {xray.order.map((index) => (
                <th scope="col" key={table.columns[index]}>
                  <bdi>{table.columns[index]}</bdi>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {xray.rows.map((row) => {
              const flagged = new Map(row.issues.map((issue) => [issue.column, issue]));
              return (
                <tr key={row.row} className={row.issues.length ? "has-issue" : undefined}>
                  <th scope="row">
                    <bdi>{row.row}</bdi>
                  </th>
                  <td className="problems">
                    <ul>
                      {row.issues.map((issue) => {
                        const peers = peersOf(xray, issue);
                        return (
                          <li key={`${issue.column}:${issue.issue}`}>
                            <IssueLabel issue={issue} />
                            {peers.length > 0 && <small> ({copy.alsoIn(peers.join(", "))})</small>}
                          </li>
                        );
                      })}
                    </ul>
                  </td>
                  {xray.order.map((index) => {
                    const column = table.columns[index];
                    const cell = row.cells[index] ?? "";
                    const issue = flagged.get(column);
                    return (
                      <td key={column} className={issue ? "flagged" : undefined}>
                        {issue && !cell.trim() ? <span className="empty-cell">{copy.empty}</span> : <bdi>{cell}</bdi>}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="xray-foot">
        {copy.showing(xray.rows.length, table.total_rows)}
        {xray.hidden > 0 && <> {copy.beyondPreview(xray.hidden)}</>}
      </p>
    </>
  );
}

function SqlView({ sql }: { sql: SqlInsight }) {
  const { t } = useLanguage();
  const copy = t.insights.sql;
  return (
    <>
      {sql.robustness_failed && (
        <div className="xray-alert" role="note">
          <strong>{copy.robustnessTitle}</strong>
          <p>{copy.robustness}</p>
        </div>
      )}
      {!sql.columns_ok && sql.columns.length > 0 && (
        <p className="xray-note">{copy.columnsWrong(sql.columns.join(", "))}</p>
      )}
      {sql.missing_regions > 0 && <p className="xray-note">{copy.missing(sql.missing_regions)}</p>}
      {sql.rows.length === 0 ? (
        <p className="xray-note">{copy.empty}</p>
      ) : (
        <div className="xray-scroll" role="region" aria-label={copy.caption} tabIndex={0}>
          <table className="xray-table sql">
            <caption className="visually-hidden">{copy.caption}</caption>
            <thead>
              <tr>
                {sql.columns.map((column) => (
                  <th scope="col" key={column}>
                    <bdi>{column}</bdi>
                  </th>
                ))}
                <th scope="col">{copy.verdict}</th>
              </tr>
            </thead>
            <tbody>
              {sql.rows.map((row, index) => {
                const ok = row.region_status === "ok";
                const wrong = [!ok, ok && !row.count_ok, ok && !row.revenue_ok];
                return (
                  <tr key={index} className={wrong.some(Boolean) ? "has-issue" : undefined}>
                    {row.cells.map((cell, column) => (
                      <td key={column} className={sql.columns_ok && wrong[column] ? "flagged" : undefined}>
                        <bdi>{cell}</bdi>
                      </td>
                    ))}
                    <td className="problems">
                      <ul className="verdicts">
                        <li className={ok ? "ok" : "bad"}>{copy.region[row.region_status]}</li>
                        {ok && <li className={row.count_ok ? "ok" : "bad"}>{row.count_ok ? copy.countOk : copy.countWrong}</li>}
                        {ok && <li className={row.revenue_ok ? "ok" : "bad"}>{row.revenue_ok ? copy.revenueOk : copy.revenueWrong}</li>}
                      </ul>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function EmailView({ email, checks }: { email: EmailInsight; checks: Check[] }) {
  const { t } = useLanguage();
  const checkTitle = useCheckTitle();
  const [active, setActive] = useState<string | null>(null);
  const segments = useMemo(() => emailSegments(email), [email]);
  const tone = new Map(email.elements.map((element) => [element.element_id, checks.findIndex((check) => check.check_id === element.check_id)]));
  const copy = t.insights.email;
  const elementLabel = (id: string) => (isEmailElementId(id) ? copy.elements[id] : id);

  return (
    <div className="email-xray">
      <figure className="email-figure">
        <figcaption>{copy.text}</figcaption>
        <div className="email-text">
          {segments.map((segment, index) =>
            segment.elements.length ? (
              <mark
                key={index}
                className={`tone-${tone.get(segment.elements[0]) ?? 0}${active && segment.elements.includes(active) ? " active" : ""}`}
              >
                {segment.text}
              </mark>
            ) : (
              <span key={index}>{segment.text}</span>
            ),
          )}
        </div>
      </figure>
      <div className="email-checklist">
        <h3>{copy.checklist}</h3>
        {checks.map((check, index) => (
          <section key={check.check_id} className={`tone-${index}`}>
            <h4>
              <span className={check.passed ? "pass-icon" : "fail-icon"}>
                <span aria-hidden="true">{check.passed ? "✓" : "!"}</span> {check.passed ? t.result.passed : t.result.failed}
              </span>{" "}
              {checkTitle(check.check_id)}
            </h4>
            <ul>
              {email.elements
                .filter((element) => element.check_id === check.check_id)
                .map((element) => {
                  const status = (
                    <>
                      <span aria-hidden="true" className="mark-icon">
                        {element.found ? "✓" : "✗"}
                      </span>
                      <span className="visually-hidden">{element.found ? copy.found : copy.missing}:</span>{" "}
                      {elementLabel(element.element_id)}
                    </>
                  );
                  return (
                    <li key={element.element_id} className={element.found ? "found" : "missing"}>
                      {element.found && element.start != null ? (
                        <button
                          type="button"
                          className="element-button"
                          aria-pressed={active === element.element_id}
                          onClick={() => setActive((current) => (current === element.element_id ? null : element.element_id))}
                        >
                          {status}
                        </button>
                      ) : (
                        status
                      )}
                    </li>
                  );
                })}
            </ul>
          </section>
        ))}
        <p className="word-meter">
          <label htmlFor="word-meter">{copy.words(email.word_count, email.min_words, email.max_words)}</label>
          <meter
            id="word-meter"
            min={0}
            max={Math.max(email.max_words + email.min_words, email.word_count)}
            low={email.min_words}
            high={email.max_words}
            optimum={(email.min_words + email.max_words) / 2}
            value={email.word_count}
          />
        </p>
      </div>
    </div>
  );
}

function XrayCard({ insights }: { insights: SubmissionInsights }) {
  const { t } = useLanguage();
  const view =
    insights.kind === "table" && insights.table ? (
      <TableView table={insights.table} issues={insights.issues} checks={insights.checks} />
    ) : insights.kind === "sql" && insights.sql ? (
      <SqlView sql={insights.sql} />
    ) : insights.kind === "email" && insights.email ? (
      <EmailView email={insights.email} checks={insights.checks} />
    ) : null;
  if (!view) return null;
  return (
    <section className="card xray-card" aria-labelledby="xray-title">
      <h2 id="xray-title">{t.insights.xrayTitle}</h2>
      <p className="insights-lead">{t.insights.xrayLead}</p>
      {view}
    </section>
  );
}

/** The impact card and the mistake X-ray for one graded, non-rejected submission. */
export function InsightsPanel({ submissionId }: { submissionId: string }) {
  const { t } = useLanguage();
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    api.insights(submissionId).then(
      (insights) => alive && setLoad({ status: "ready", insights }),
      () => alive && setLoad({ status: "error" }),
    );
    return () => {
      alive = false;
    };
  }, [submissionId, attempt]);

  function retry() {
    setLoad({ status: "loading" });
    setAttempt((count) => count + 1);
  }

  if (load.status === "loading")
    return (
      <section className="card xray-card loading" aria-busy="true">
        <p role="status">{t.insights.loading}</p>
      </section>
    );
  if (load.status === "error")
    return (
      <section className="card xray-card">
        <p className="inline-error">{t.insights.unavailable}</p>
        <button type="button" className="secondary compact" onClick={retry}>
          {t.insights.retry}
        </button>
      </section>
    );
  if (load.insights.rejected_code) return null;
  return (
    <>
      <ImpactCard impact={load.insights.impact} />
      <XrayCard insights={load.insights} />
    </>
  );
}
