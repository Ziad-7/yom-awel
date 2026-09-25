import { useLanguage } from "../lib/i18n/language";

export function TarekAvatar({ size = "medium" }: { size?: "medium" | "small" }) {
  return (
    <svg className={`tarek-avatar ${size}`} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <circle cx="24" cy="24" r="24" className="tarek-bg" />
      <circle cx="24" cy="19" r="8" className="tarek-face" />
      <path d="M9 42c2.5-8 8-12 15-12s12.5 4 15 12" className="tarek-body" />
    </svg>
  );
}

export function PersonaHeader() {
  const { t } = useLanguage();
  return (
    <div className="persona">
      <TarekAvatar />
      <div>
        <strong>{t.persona.name}</strong>
        <small>{t.persona.role}</small>
      </div>
    </div>
  );
}
