"use client";
import { useRef, useState } from "react";
import { ApiError } from "../lib/api/client";
import type { CoachAnswer } from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { useLanguage } from "../lib/i18n/language";
import { directionOf, fromApiLanguage, toApiLanguage } from "../lib/i18n/keys";
import { errorMessage } from "../lib/messages";
import { TarekAvatar } from "./persona";

type Turn = { question: string; answer: CoachAnswer };
const MAX_QUESTION = 300;

/** A short, grounded conversation about one graded submission. */
export function AskTarek({ submissionId }: { submissionId: string }) {
  const { lang, t } = useLanguage();
  const copy = t.ask;
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    setError("");
    setPending(trimmed);
    try {
      const answer = await api.ask(submissionId, trimmed.slice(0, MAX_QUESTION), toApiLanguage(lang));
      setTurns((current) => [...current, { question: trimmed, answer }]);
      setQuestion("");
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 429 ? copy.busy : errorMessage(t, cause));
    } finally {
      setPending(null);
      input.current?.focus();
    }
  }

  return (
    <section className="card ask-card" aria-labelledby="ask-title">
      <div className="ask-head">
        <TarekAvatar />
        <h2 id="ask-title">{copy.title}</h2>
      </div>
      <p className="insights-lead">{copy.lead}</p>
      {turns.length > 0 && (
        <ol className="ask-thread" aria-label={copy.title}>
          {turns.map((turn, index) => {
            const answerLang = fromApiLanguage(turn.answer.language);
            return (
              <li key={index}>
                <p className="ask-question">
                  <span className="visually-hidden">{copy.you}: </span>
                  {turn.question}
                </p>
                <div className={`ask-answer ${turn.answer.source}`} lang={answerLang} dir={directionOf(answerLang)}>
                  <p>{turn.answer.answer}</p>
                  <small className="ask-source">{turn.answer.source === "gemini" ? copy.ai : copy.guide}</small>
                  {turn.answer.grounded_on.length > 0 && (
                    <details className="ask-facts">
                      <summary>{copy.basedOn}</summary>
                      <ul>
                        {turn.answer.grounded_on.map((fact) => (
                          <li key={fact}>{fact}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      <div role="status" aria-live="polite" className="ask-status">
        {pending ? copy.thinking : ""}
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="ask-suggestions">
        {copy.suggestions.map((suggestion) => (
          <button key={suggestion} type="button" className="chip" disabled={pending !== null} onClick={() => void ask(suggestion)}>
            {suggestion}
          </button>
        ))}
      </div>
      <form
        className="ask-form"
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
      >
        <label htmlFor="ask-input" className="visually-hidden">
          {copy.label}
        </label>
        <input
          id="ask-input"
          ref={input}
          value={question}
          maxLength={MAX_QUESTION}
          placeholder={copy.placeholder}
          disabled={pending !== null}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button className="primary" disabled={pending !== null || !question.trim()}>
          {copy.send}
        </button>
      </form>
    </section>
  );
}
