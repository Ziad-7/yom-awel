"use client";
import { useLanguage } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";

export function LanguageToggle({
  onChange,
  disabled = false,
}: {
  onChange: (lang: Lang) => void;
  disabled?: boolean;
}) {
  const { lang, t } = useLanguage();
  const next: Lang = lang === "ar" ? "en" : "ar";
  return (
    <button
      type="button"
      className="lang-toggle"
      aria-label={t.language.switchLabel}
      disabled={disabled}
      onClick={() => onChange(next)}
    >
      <span aria-hidden="true">⇄</span>
      <span lang={t.language.switchLang}>{t.language.switchTo}</span>
    </button>
  );
}
