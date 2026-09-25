import { useState } from "react";
import { useLanguage } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";

export function Onboarding({
  disabled,
  onLanguage,
  onSubmit,
}: {
  disabled: boolean;
  onLanguage: (lang: Lang) => void;
  onSubmit: (name: string) => void;
}) {
  const { lang, t } = useLanguage();
  const [name, setName] = useState("");
  return (
    <div className="welcome-grid">
      <section className="welcome-card" aria-labelledby="welcome-title">
        <span className="section-tag">{t.onboarding.tag}</span>
        <h2 id="welcome-title">{t.onboarding.heading}</h2>
        <p>{t.onboarding.body}</p>
        <ol className="welcome-steps">
          {t.onboarding.steps.map((step, index) => (
            <li key={step}>
              <b>0{index + 1}</b> {step}
            </li>
          ))}
        </ol>
      </section>
      <form
        className="join-card"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim()) onSubmit(name.trim());
        }}
      >
        <h2>{t.onboarding.formTitle}</h2>
        <p>{t.onboarding.formHint}</p>
        <label htmlFor="name">{t.onboarding.nameLabel}</label>
        <input
          id="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={80}
          required
          autoComplete="given-name"
          placeholder={t.onboarding.namePlaceholder}
        />
        <fieldset className="language-choice">
          <legend>{t.onboarding.languageLegend}</legend>
          {(["ar", "en"] as const).map((option) => (
            <label key={option} lang={option}>
              <input
                type="radio"
                name="language"
                value={option}
                checked={lang === option}
                onChange={() => onLanguage(option)}
              />
              {option === "ar" ? t.onboarding.arabic : t.onboarding.english}
            </label>
          ))}
        </fieldset>
        <button className="primary" disabled={disabled || !name.trim()}>
          {t.onboarding.submit} <span aria-hidden="true" className="arrow" />
        </button>
        <small>{t.onboarding.privacy}</small>
      </form>
    </div>
  );
}
