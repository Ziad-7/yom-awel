"use client";
import { useEffect, useState, useSyncExternalStore } from "react";
import type { FeedbackResult } from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { parseFeedback, type FeedbackSection } from "../lib/feedback";
import { dictionaries } from "../lib/i18n/dictionaries";
import { useLanguage } from "../lib/i18n/language";
import { directionOf, fromApiLanguage, type ApiLanguage, type Lang } from "../lib/i18n/keys";
import { errorMessage } from "../lib/messages";
import { TarekAvatar } from "./persona";

const ICONS: Record<FeedbackSection, string> = {
  decision: "M5 21V4m0 0h11l-2 4 2 4H5",
  impact: "M3 6l6 6 4-4 8 8m0 0v-5m0 5h-5",
  next: "M4 12h15m0 0l-6-6m6 6l-6 6",
  score: "M12 3a9 9 0 1 0 9 9M12 12l6-6",
};

function SectionIcon({ id }: { id: FeedbackSection }) {
  return (
    <svg className={`section-icon is-${id}`} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={ICONS[id]} />
    </svg>
  );
}

/**
 * feedback_text opens with Tarek's own byline, so the card never repeats his name. Text that
 * follows the four-section contract is shown as labelled blocks; anything else as plain prose.
 */
function FeedbackText({ text, lang, passed }: { text: string; lang: Lang; passed: boolean }) {
  const parsed = parseFeedback(text, lang);
  if (!parsed)
    return (
      <p className="feedback-text" lang={lang} dir={directionOf(lang)}>
        {text.trim()}
      </p>
    );
  const labels = dictionaries[lang].feedback.sections;
  return (
    <div className="feedback-text structured" lang={lang} dir={directionOf(lang)}>
      {parsed.byline && <p className="feedback-byline">{parsed.byline}</p>}
      <div className="feedback-sections">
        {parsed.sections.map((section) => (
          <section key={section.id} className={`feedback-section is-${section.id}${section.id === "decision" ? (passed ? " accepted" : " rework") : ""}`}>
            <h3>
              <SectionIcon id={section.id} />
              {labels[section.id]}
            </h3>
            <p>{section.body}</p>
          </section>
        ))}
      </div>
    </div>
  );
}

const noSubscription = () => () => {};
const speechSupported = () => "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;

/** Reads the feedback aloud with the browser's own speech engine; nothing leaves the device. */
function useReadAloud() {
  const supported = useSyncExternalStore(noSubscription, speechSupported, () => false);
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => () => {
    if (speechSupported()) window.speechSynthesis.cancel();
  }, []);

  function stop() {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }
  function speak(text: string, lang: Lang) {
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === "ar" ? "ar-EG" : "en-US";
    const voice = synth.getVoices().find((item) => item.lang.toLowerCase().startsWith(lang));
    if (voice) utterance.voice = voice;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.speak(utterance);
    setSpeaking(true);
  }
  return { supported, speaking, speak, stop };
}

function spokenText(text: string, lang: Lang) {
  const parsed = parseFeedback(text, lang);
  if (!parsed) return text;
  const labels = dictionaries[lang].feedback.sections;
  return [parsed.byline, ...parsed.sections.map((section) => `${labels[section.id]}. ${section.body}`)].join("\n");
}

export function FeedbackCard({ submissionId, initial, passed }: { submissionId: string; initial: FeedbackResult; passed: boolean }) {
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
  const voice = useReadAloud();

  async function toggle() {
    setError("");
    voice.stop();
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
        {voice.supported && (
          <button
            type="button"
            className="secondary compact listen"
            aria-pressed={voice.speaking}
            onClick={() => (voice.speaking ? voice.stop() : voice.speak(spokenText(feedback.feedback_text, shownLang), shownLang))}
          >
            <span aria-hidden="true">{voice.speaking ? "■" : "▶"}</span> {voice.speaking ? t.feedback.stop : t.feedback.listen}
          </button>
        )}
      </div>
      <div role="status" aria-live="polite" className="loading-status">
        {loading ? t.feedback.loading : ""}
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <FeedbackText text={feedback.feedback_text} lang={shownLang} passed={passed} />
      <p className="feedback-source">{feedback.used_fallback ? t.feedback.fallback : t.feedback.ai}</p>
    </section>
  );
}
