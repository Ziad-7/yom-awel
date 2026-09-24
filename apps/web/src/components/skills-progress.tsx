import type { Attempt, SkillsProfile, TaskSummary } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";
import { isSkillId } from "../lib/i18n/keys";

type SkillsProgressProps = {
  skills: SkillsProfile | null;
  attempts: Attempt[];
  tasks: TaskSummary[];
  canRetry: boolean;
  onRetry: () => void;
  onWork: () => void;
  onViewAttempt: (attempt: Attempt) => void;
};

function SkillBars({ skills, onWork }: { skills: SkillsProfile | null; onWork: () => void }) {
  const { t } = useLanguage();
  if (!skills?.skills.length)
    return (
      <div className="empty-state">
        <span aria-hidden="true">◇</span>
        <p>{t.skills.empty}</p>
        <button type="button" className="secondary" onClick={onWork}>
          {t.skills.goToWork} <span aria-hidden="true" className="arrow" />
        </button>
      </div>
    );
  return (
    <div className="skill-grid">
      {skills.skills.map((skill) => {
        const name = isSkillId(skill.skill_id) ? t.skills.names[skill.skill_id] : skill.skill_id;
        return (
          <article className="skill-card" key={skill.skill_id}>
            <h3>{name}</h3>
            <strong>
              <bdi>{skill.score}</bdi>
              <small> / 100</small>
            </strong>
            <progress value={skill.score} max={100} aria-label={name} />
            <p>{t.skills.basis}</p>
          </article>
        );
      })}
    </div>
  );
}

function AttemptTimeline({ attempts, onView }: { attempts: Attempt[]; onView: (attempt: Attempt) => void }) {
  const { t } = useLanguage();
  if (!attempts.length) return <p className="muted">{t.skills.noAttempts}</p>;
  return (
    <ol className="attempt-timeline">
      {[...attempts].reverse().map((attempt) => (
        <li key={attempt.submission_id} className={attempt.evaluation.passed ? "passed" : "failed"}>
          <span className="dot" aria-hidden="true">
            {attempt.evaluation.passed ? "✓" : "!"}
          </span>
          <div>
            <strong>{t.skills.attempt(attempt.attempt_number)}</strong>
            <small>{attempt.evaluation.passed ? t.result.passed : t.result.failed}</small>
          </div>
          <bdi className="points">{attempt.evaluation.score}/100</bdi>
          <button type="button" className="text-button" onClick={() => onView(attempt)}>
            {t.skills.viewResult}
          </button>
        </li>
      ))}
    </ol>
  );
}

export function SkillsProgress(props: SkillsProgressProps) {
  const { lang, t } = useLanguage();
  return (
    <div className="skills-layout">
      <section className="card" aria-labelledby="skills-title">
        <h2 id="skills-title">{t.skills.title}</h2>
        <SkillBars skills={props.skills} onWork={props.onWork} />
      </section>
      <section className="card" aria-labelledby="status-title">
        <h2 id="status-title">{t.skills.taskStatus}</h2>
        <ul className="status-list">
          {props.tasks.map((task) => (
            <li key={task.task_id}>
              <span>{lang === "ar" ? task.title_ar : task.title_en}</span>
              <span className={`pill status-${task.status}`}>{t.catalogue.status[task.status]}</span>
            </li>
          ))}
        </ul>
        {props.canRetry && (
          <button type="button" className="primary" onClick={props.onRetry}>
            {t.skills.retryPath} <span aria-hidden="true">↑</span>
          </button>
        )}
      </section>
      <section className="card" aria-labelledby="attempts-title">
        <div className="section-heading">
          <h2 id="attempts-title">{t.skills.attempts}</h2>
          <span className="muted">{t.skills.attemptsCount(props.attempts.length)}</span>
        </div>
        <AttemptTimeline attempts={props.attempts} onView={props.onViewAttempt} />
      </section>
    </div>
  );
}
