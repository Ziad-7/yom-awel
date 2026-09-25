"use client";
import { useState } from "react";
import type { FeedbackResult } from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { dictionaries } from "../lib/i18n/dictionaries";
import { useLanguage } from "../lib/i18n/language";
import { directionOf, fromApiLanguage, type ApiLanguage, type Lang } from "../lib/i18n/keys";
import { errorMessage } from "../lib/messages";
import { TarekAvatar } from "./persona";

/** feedback_text opens with Tarek's own byline, so the card never repeats his name. */
function FeedbackText({ text, lang }: { text: string; lang: Lang }) {
  return (
    <p className="feedback-text" lang={lang} dir={directionOf(lang)}>
      {text.trim()}
    </p>
  );
}

export function FeedbackCard({ submissionId, initial }: { submissionId: string; initial: FeedbackResult }) {
  const { t } = useLanguage();
  const [versions, setVersions] = useState<Partial<Record<ApiLanguage, FeedbackResult>>>({
    [initial.language]: initial,
  });
  const [shown, setShown] = useState<ApiLanguage>(initial.language);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const feedback = versions[shown] ?? initial;
  const shownLang = fromApiLanguage(shown);
  const copy = dictionaries[shownLang].feedback;
  const target: ApiLanguage = shown === "ar-EG" ? "en" : "ar-EG";

  async function toggle() {
    setError("");
    if (versions[target]) return setShown(target);
    setLoading(true);
    try {
      const next = await api.feedback(submissionId, target);
      setVersions((current) => ({ ...current, [target]: next }));
      setShown(target);
    } catch (cause) {
      setError(errorMessage(t, cause));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card feedback-card" aria-labelledby="feedback-title" aria-busy={loading}>
      <div className="feedback-head">
        <TarekAvatar />
        <h2 id="feedback-title">{t.feedback.title}</h2>
        <button
          type="button"
          className="secondary compact"
          lang={copy.toggleLang}
          onClick={() => void toggle()}
          disabled={loading}
        >
          {copy.toggle}
        </button>
      </div>
      <div role="status" aria-live="polite" className="loading-status">
        {loading ? t.feedback.loading : ""}
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <FeedbackText text={feedback.feedback_text} lang={shownLang} />
      <p className="feedback-source">{feedback.used_fallback ? t.feedback.fallback : t.feedback.ai}</p>
    </section>
  );
}
