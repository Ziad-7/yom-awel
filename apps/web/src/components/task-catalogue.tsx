import type { TaskSummary } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";

function TaskCard({ task, disabled, onOpen }: { task: TaskSummary; disabled: boolean; onOpen: () => void }) {
  const { lang, t } = useLanguage();
  const title = lang === "ar" ? task.title_ar : task.title_en;
  return (
    <article className="task-tile" aria-labelledby={`task-${task.task_id}`}>
      <div className="tile-top">
        <span className="file-icon" aria-hidden="true">
          {task.task_id === "sql-report" ? "SQL" : task.task_id === "client-email" ? "TXT" : "CSV"}
        </span>
        <span className={`pill status-${task.status}`}>{t.catalogue.status[task.status]}</span>
      </div>
      <h3 id={`task-${task.task_id}`}>{title}</h3>
      <p className="tile-meta">
        {t.catalogue.points(task.points_total)} <span aria-hidden="true">·</span>{" "}
        {t.catalogue.passAt(task.pass_threshold)}
      </p>
      <button type="button" className="primary" disabled={disabled} onClick={onOpen}>
        {t.catalogue.action[task.status]} <span aria-hidden="true" className="arrow" />
      </button>
    </article>
  );
}

export function TaskCatalogue({
  tasks,
  disabled,
  onOpen,
}: {
  tasks: TaskSummary[];
  disabled: boolean;
  onOpen: (task: TaskSummary) => void;
}) {
  const { t } = useLanguage();
  return (
    <section className="catalogue" aria-labelledby="catalogue-title">
      <h2 id="catalogue-title">{t.catalogue.title}</h2>
      <div className="tile-grid">
        {tasks.map((task) => (
          <TaskCard key={task.task_id} task={task} disabled={disabled} onOpen={() => onOpen(task)} />
        ))}
      </div>
    </section>
  );
}
