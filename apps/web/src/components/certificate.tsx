"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError } from "../lib/api/client";
import type { Certificate } from "../lib/api/contract";
import { api } from "../lib/api/endpoints";
import { directionOf, isCheckId, isSkillId, type Lang } from "../lib/i18n/keys";
import { LanguageProvider, useLanguage } from "../lib/i18n/language";
import { QrCode } from "./qr-code";

const LOCALE: Record<Lang, string> = { ar: "ar-EG-u-nu-latn", en: "en-GB" };
const formatDate = (value: string, lang: Lang, time = false) =>
  new Intl.DateTimeFormat(LOCALE[lang], time ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(new Date(value));

/** The sharer's language travels with the link, so the reader opens it the way it was shared. */
export const certificateUrl = (token: string, lang: Lang) => `${window.location.origin}/verify/${token}?lang=${lang}`;

/** The certificate itself, shared by the learner's card and the public verify page. */
export function CertificateBody({ certificate }: { certificate: Certificate }) {
  const { lang, t } = useLanguage();
  const copy = t.certificate;
  const check = (id: string) => (isCheckId(id) ? t.checks[id].title : id);
  return (
    <div className="certificate-body">
      <p className="certificate-issuer">{copy.issuer}</p>
      <p className="certificate-awarded">
        <small>{copy.awardedTo}</small>
        <bdi>{certificate.display_name}</bdi>
      </p>
      <h3>{copy.tasks}</h3>
      <ul className="certificate-tasks">
        {certificate.tasks.map((task) => (
          <li key={task.task_id}>
            <strong>{lang === "ar" ? task.title_ar : task.title_en}</strong>
            <span>
              <bdi>{task.score}/100</bdi> · {copy.attempts(task.attempts)} · <time dateTime={task.passed_at}>{formatDate(task.passed_at, lang)}</time>
            </span>
          </li>
        ))}
      </ul>
      <h3>{copy.skills}</h3>
      <ul className="certificate-skills">
        {certificate.skills.map((skill) => (
          <li key={skill.skill_id}>
            <strong>{isSkillId(skill.skill_id) ? t.skills.names[skill.skill_id] : skill.skill_id}</strong>
            <small>
              {copy.evidence}: {skill.evidence.map(check).join(lang === "ar" ? "، " : ", ")}
            </small>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Load = { status: "loading" } | { status: "none" } | { status: "ready"; certificate: Certificate };

/** On the skills page: the learner's own certificate with a link, copy button and QR code. */
export function CertificateCard() {
  const { lang, t } = useLanguage();
  const copy = t.certificate;
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    api.myCertificate().then(
      (certificate) => alive && setLoad({ status: "ready", certificate }),
      () => alive && setLoad({ status: "none" }),
    );
    return () => {
      alive = false;
    };
  }, []);

  if (load.status === "loading") return null;
  if (load.status === "none")
    return (
      <section className="card certificate-card locked" aria-labelledby="certificate-title">
        <h2 id="certificate-title">{copy.title}</h2>
        <p className="insights-lead">{copy.locked}</p>
      </section>
    );
  const { certificate } = load;
  const url = certificateUrl(certificate.token, lang);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="card certificate-card" aria-labelledby="certificate-title">
      <div className="certificate-head">
        <h2 id="certificate-title">{copy.title}</h2>
        <span className="verified-badge">✓ {copy.verified}</span>
      </div>
      <p className="insights-lead">{copy.lead}</p>
      <div className="certificate-layout">
        <CertificateBody certificate={certificate} />
        <div className="certificate-share">
          <QrCode value={url} label={copy.qr(certificate.display_name)} />
          <label htmlFor="certificate-link">{copy.link}</label>
          <input id="certificate-link" readOnly value={url} dir="ltr" onFocus={(event) => event.currentTarget.select()} />
          <div className="certificate-actions">
            <button type="button" className="secondary compact" onClick={() => void copyLink()}>
              {copy.copy}
            </button>
            <a className="secondary compact" href={url} target="_blank" rel="noopener noreferrer">
              {copy.open}
            </a>
          </div>
          <p role="status" className="copy-status">
            {copied ? copy.copied : ""}
          </p>
        </div>
      </div>
    </section>
  );
}

type Verify = { status: "loading" } | { status: "invalid" } | { status: "offline" } | { status: "ready"; certificate: Certificate };

/** The public page an employer opens: no session, read-only, verified on every visit. */
export function CertificateVerification({ token, lang }: { token: string; lang?: Lang }) {
  const { lang: current } = useLanguage();
  const initial = lang ?? current;
  return (
    <LanguageProvider initialLang={initial}>
      <Verification token={token} />
    </LanguageProvider>
  );
}

function Verification({ token }: { token: string }) {
  const { lang, t, setLang } = useLanguage();
  const copy = t.certificate;
  const [state, setState] = useState<Verify>({ status: "loading" });

  useEffect(() => {
    let alive = true;
    api.certificate(token).then(
      (certificate) => alive && setState({ status: "ready", certificate }),
      (cause: unknown) => alive && setState({ status: cause instanceof ApiError && cause.status >= 400 && cause.status < 500 ? "invalid" : "offline" }),
    );
    return () => {
      alive = false;
    };
  }, [token]);

  return (
    <main id="main" className="verify-page" lang={lang} dir={directionOf(lang)}>
      <div className="verify-top">
        <Link href="/" className="brand-link">
          {t.shell.brand}
        </Link>
        <button type="button" className="secondary compact" lang={t.language.switchLang} onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          {t.language.switchTo}
        </button>
      </div>
      {state.status === "loading" && <p role="status">{copy.loading}</p>}
      {state.status === "offline" && (
        <p className="inline-error" role="alert">
          {t.errors.offline}
        </p>
      )}
      {state.status === "invalid" && (
        <section className="card certificate-card invalid" aria-labelledby="verify-title">
          <h1 id="verify-title">{copy.invalidTitle}</h1>
          <p>{copy.invalidBody}</p>
          <Link href="/" className="primary">
            {copy.home}
          </Link>
        </section>
      )}
      {state.status === "ready" && (
        <section className="card certificate-card public" aria-labelledby="verify-title">
          <div className="certificate-head">
            <h1 id="verify-title">{copy.title}</h1>
            <span className="verified-badge">✓ {copy.verified}</span>
          </div>
          <p className="insights-lead">{copy.verifiedAt(formatDate(state.certificate.verified_at, lang, true))}</p>
          <CertificateBody certificate={state.certificate} />
          <div className="certificate-actions no-print">
            <button type="button" className="secondary compact" onClick={() => window.print()}>
              {copy.print}
            </button>
            <Link href="/" className="secondary compact">
              {copy.home}
            </Link>
          </div>
        </section>
      )}
    </main>
  );
}
