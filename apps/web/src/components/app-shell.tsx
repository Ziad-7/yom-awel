import Link from "next/link";
import type { Learner, Runtime } from "../lib/api/contract";
import { useLanguage } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import type { View } from "../lib/use-workplace";
import { LanguageToggle } from "./language-toggle";

const VIEWS: { view: View; icon: string }[] = [
  { view: "tasks", icon: "☰" },
  { view: "work", icon: "▦" },
  { view: "skills", icon: "↗" },
];

type ShellProps = {
  view: View;
  learner: Learner | null;
  runtime: Runtime | null;
  canWork: boolean;
  languageBusy: boolean;
  onNavigate: (view: View) => void;
  onLanguage: (lang: Lang) => void;
  onRestart: () => void;
  children: React.ReactNode;
};

function Navigation({ view, canWork, onNavigate }: Pick<ShellProps, "view" | "canWork" | "onNavigate">) {
  const { t } = useLanguage();
  return (
    <nav aria-label={t.shell.navLabel}>
      {VIEWS.filter((item) => item.view !== "work" || canWork).map((item) => (
        <button
          key={item.view}
          type="button"
          className={view === item.view ? "nav-item active" : "nav-item"}
          aria-current={view === item.view ? "page" : undefined}
          onClick={() => onNavigate(item.view)}
        >
          <span aria-hidden="true">{item.icon}</span> {t.shell.nav[item.view]}
        </button>
      ))}
    </nav>
  );
}

function RuntimeBadges({ runtime }: { runtime: Runtime }) {
  const { t } = useLanguage();
  return (
    <span className="runtime-badges">
      <span className="badge">
        <i aria-hidden="true" /> {runtime.mode === "cloud" ? t.shell.modeCloud : t.shell.modeLocal}
      </span>
      <span className="badge">
        {runtime.feedback_provider === "gemini" ? t.shell.providerGemini : t.shell.providerDeterministic}
      </span>
    </span>
  );
}

export function AppShell(props: ShellProps) {
  const { t } = useLanguage();
  const { learner, runtime, view } = props;
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label={t.shell.home}>
          <span className="brand-mark" aria-hidden="true">
            ي
          </span>
          <span>
            {t.shell.brand}
            <small>{t.shell.tagline}</small>
          </span>
        </Link>
        {learner && <Navigation view={view} canWork={props.canWork} onNavigate={props.onNavigate} />}
        <div className="side-note">
          <span className="spark" aria-hidden="true">
            ✳
          </span>
          <p className="side-title">{t.shell.sideTitle}</p>
          <p>{t.shell.sideBody}</p>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar small" aria-hidden="true">
            {learner?.display_name.slice(0, 1) || "؟"}
          </span>
          <div>
            <bdi>{learner?.display_name || t.shell.guest}</bdi>
            <small>{learner ? t.shell.role : t.shell.guestHint}</small>
          </div>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <span className="crumb">
            {t.shell.area} <span className="slash" aria-hidden="true">/</span>{" "}
            <strong>{learner ? t.shell.nav[view] : t.onboarding.tag}</strong>
          </span>
          <div className="top-actions">
            {runtime && <RuntimeBadges runtime={runtime} />}
            <LanguageToggle onChange={props.onLanguage} disabled={props.languageBusy} />
            {learner && (
              <button type="button" className="text-button" onClick={props.onRestart}>
                {t.restart.open}
              </button>
            )}
          </div>
        </header>
        {props.children}
      </div>
    </div>
  );
}

export function PageHeading({ title }: { title: string }) {
  const { t } = useLanguage();
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{t.headings.eyebrow}</p>
        <h1>{title}</h1>
        <p>{t.headings.lead}</p>
      </div>
      <span className="day-chip">
        {t.shell.day} <b>01</b>
      </span>
    </div>
  );
}
