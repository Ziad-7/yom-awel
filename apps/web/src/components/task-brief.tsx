import type { TaskDetail } from "../lib/api/contract";
import { datasetHref } from "../lib/api/endpoints";
import { useLanguage } from "../lib/i18n/language";
import { isCheckId } from "../lib/i18n/keys";
import { Markdown } from "./markdown";
import { PersonaHeader } from "./persona";

export function CheckList({ task }: { task: TaskDetail }) {
  const { t } = useLanguage();
  return (
    <section className="card" aria-labelledby="checks-title">
      <h2 id="checks-title">{t.workspace.checks}</h2>
      <ul className="check-list">
        {task.checks.map((check) => {
          const copy = isCheckId(check.check_id) ? t.checks[check.check_id] : null;
          return (
            <li key={check.check_id}>
              <div>
                <strong>{copy?.title ?? check.check_id}</strong>
                {check.critical && <span className="badge critical">{t.workspace.critical}</span>}
                {copy && <p>{copy.description}</p>}
              </div>
              <span className="points">
                <bdi>{t.workspace.points(check.points)}</bdi>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="muted">{t.workspace.passRule(task.pass_threshold)}</p>
    </section>
  );
}

export function DatasetDownloads({ task }: { task: TaskDetail }) {
  const { t } = useLanguage();
  const labels = { csv: t.workspace.downloadCsv, xlsx: t.workspace.downloadXlsx };
  const hint = task.task_id === "sql-report"
    ? t.workspace.sqlDatasetHint
    : task.task_id === "client-email"
      ? t.workspace.emailDatasetHint
      : t.workspace.datasetHint;
  return (
    <section className="file-card" aria-labelledby="dataset-title">
      <div className="file-icon" aria-hidden="true">
        CSV
      </div>
      <div className="file-text">
        <h2 id="dataset-title">{t.workspace.dataset}</h2>
        <small>{hint}</small>
      </div>
      <div className="file-actions">
        {task.formats.map((format) => (
          <a key={format} className="secondary" href={datasetHref(task.task_id, format)} download>
            {labels[format]} <span aria-hidden="true">↓</span>
          </a>
        ))}
      </div>
    </section>
  );
}

export function TaskBrief({ task }: { task: TaskDetail }) {
  const { lang, t } = useLanguage();
  const brief = lang === "ar" ? task.brief_ar : task.brief_en;
  const hints = lang === "ar" ? task.hints_ar : task.hints_en;
  const intro = task.task_id === "sql-report"
    ? t.persona.introSql
    : task.task_id === "client-email"
      ? t.persona.introEmail
      : t.persona.intro;
  return (
    <section className="card task-card" aria-labelledby="brief-title">
      <PersonaHeader />
      <p className="persona-intro">{intro}</p>
      <h2 id="brief-title" className="visually-hidden">
        {t.workspace.brief}
      </h2>
      <Markdown source={brief} />
      <details className="hints">
        <summary>{t.workspace.hints}</summary>
        <Markdown source={hints} headingBase={4} />
      </details>
    </section>
  );
}
