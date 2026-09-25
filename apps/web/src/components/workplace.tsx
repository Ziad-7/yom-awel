"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  downloadDataset,
  request,
  type Schema,
} from "../lib/api/client";
import { endSession, startSession } from "../lib/auth";
import { uploadFile, validateFile } from "../lib/uploads";

type Outcome = Schema["SubmissionOutcome"];
const TASK_ID = "clean-sales";
type Pending = {
  body: Schema["SubmissionInput"];
  key: string;
  submissionId?: string;
};
const skillNames: Record<string, string> = {
  data_cleaning: "تنظيف البيانات",
  attention_to_detail: "الانتباه للتفاصيل",
  sql_querying: "استعلامات SQL",
  business_communication: "التواصل المهني",
};

export default function Workplace({
  initialView = "work",
}: {
  initialView?: "work" | "skills";
}) {
  const [view, setView] = useState(initialView);
  const [runtime, setRuntime] = useState<Schema["RuntimeResult"] | null>(null);
  const [name, setName] = useState("");
  const [user, setUser] = useState<Schema["Learner"] | null>(null);
  const [task, setTask] = useState<Schema["CurrentTaskResult"] | null>(null);
  const [skills, setSkills] = useState<Schema["SkillsProfile"] | null>(null);
  const [history, setHistory] = useState<Schema["AttemptResult"][]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [booting, setBooting] = useState(true);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const errorHeading = useRef<HTMLDivElement>(null);
  const nameInput = useRef<HTMLInputElement>(null);

  const clear = useCallback(() => {
    setUser(null);
    setTask(null);
    setSkills(null);
    setHistory([]);
    setOutcome(null);
    setPending(null);
    setFile(null);
  }, []);
  const refresh = useCallback(async () => {
    const [current, profile, attempts] = await Promise.all([
      request<Schema["CurrentTaskResult"]>("/api/v1/tasks/current"),
      request<Schema["SkillsProfile"]>("/api/v1/skills"),
      request<Schema["AttemptResult"][]>("/api/v1/attempts"),
    ]);
    setTask(current);
    setSkills(profile);
    setHistory(attempts);
  }, []);
  const report = useCallback(
    (cause: unknown) => {
      if (cause instanceof ApiError && cause.status === 401) clear();
      setError(
        cause instanceof Error ? cause.message : "حصلت مشكلة. جرّب تاني.",
      );
    },
    [clear],
  );

  useEffect(() => {
    let alive = true;
    async function restore() {
      try {
        const config =
          await request<Schema["RuntimeResult"]>("/api/v1/runtime");
        if (!alive) return;
        setRuntime(config);
        try {
          const learner = await request<Schema["Learner"]>(
            "/api/v1/learners/me",
          );
          await refresh();
          if (alive) {
            setUser(learner);
            const saved = sessionStorage.getItem("yom-awel.pending");
            if (saved) {
              try {
                const item = JSON.parse(saved);
                if (item.learnerId === learner.learner_id)
                  setPending(item.pending);
              } catch {
                sessionStorage.removeItem("yom-awel.pending");
              }
            }
          }
        } catch (cause) {
          if (!(
            cause instanceof ApiError &&
            (cause.status === 401 || cause.status === 404)
          ))
            throw cause;
        }
      } catch (cause) {
        if (alive) report(cause);
      } finally {
        if (alive) setBooting(false);
      }
    }
    void restore();
    return () => {
      alive = false;
    };
  }, [refresh, report]);
  useEffect(() => {
    if (outcome) resultHeading.current?.focus();
  }, [outcome]);
  useEffect(() => {
    if (error) errorHeading.current?.focus();
  }, [error]);

  useEffect(() => {
    if (!user) return;
    if (pending)
      sessionStorage.setItem(
        "yom-awel.pending",
        JSON.stringify({ learnerId: user.learner_id, pending }),
      );
    else sessionStorage.removeItem("yom-awel.pending");
  }, [pending, user]);

  async function begin(event: React.FormEvent) {
    event.preventDefault();
    if (!runtime) return;
    setBusy("بنجهّز مكتبك…");
    setError("");
    try {
      await startSession();
      const learner = await request<Schema["Learner"]>(
        "/api/v1/learners/onboard",
        {
          method: "POST",
          body: JSON.stringify({
            display_name: name.trim(),
            preferred_language: "ar-EG",
          }),
        },
      );
      await request<Schema["CurrentTaskResult"]>(
        `/api/v1/tasks/${TASK_ID}/start`,
        { method: "POST" },
      );
      setUser(learner);
      await refresh();
    } catch (cause) {
      report(cause);
    } finally {
      setBusy("");
    }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!task?.task || (!file && !pending)) return;
    setError("");
    setBusy(pending ? "بنتأكد من نتيجة التسليم…" : "بنرفع الملف بأمان…");
    try {
      let attempt = pending;
      if (!attempt) {
        const artifact = await uploadFile(file!);
        attempt = {
          key: crypto.randomUUID(),
          body: { ...artifact, task_version_id: task.task.task_version_id },
        };
        setPending(attempt);
      }
      setBusy("بنراجع التسليم…");
      const result = await request<Outcome | Schema["ProcessingState"]>(
        "/api/v1/submissions",
        {
          method: "POST",
          headers: { "Idempotency-Key": attempt.key },
          body: JSON.stringify(attempt.body),
        },
      );
      if ("evaluation" in result) {
        setOutcome(result);
        setPending(null);
        setFile(null);
        await refresh();
      } else {
        setPending({ ...attempt, submissionId: result.submission_id });
        setError("التسليم لسه قيد المراجعة. استخدم تحقق من النتيجة بعد شوية.");
      }
    } catch (cause) {
      report(cause);
    } finally {
      setBusy("");
    }
  }
  async function download(format: "csv" | "xlsx") {
    setError("");
    try {
      await downloadDataset(TASK_ID, format);
    } catch (cause) {
      report(cause);
    }
  }
  async function logout() {
    try {
      await endSession();
      clear();
      setName("");
      setLogoutOpen(false);
    } catch (cause) {
      report(cause);
    }
  }
  const completed =
    task?.status === "TASK_COMPLETED" || task?.status === "PROGRAM_COMPLETED";

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="يوم أول، الرئيسية">
          <span className="brand-mark">ي</span>
          <span>
            يوم أول<small>خبرتك بتبدأ هنا</small>
          </span>
        </Link>
        <div className="workspace-label">
          مساحة العمل <span>01</span>
        </div>
        <nav aria-label="التنقل الرئيسي">
          <button
            className={view === "work" ? "nav-item active" : "nav-item"}
            onClick={() => setView("work")}
            aria-current={view === "work" ? "page" : undefined}
          >
            <span aria-hidden="true">▦</span> مكتبي <span className="nav-dot" />
          </button>
          <button
            className={view === "skills" ? "nav-item active" : "nav-item"}
            onClick={() => setView("skills")}
            aria-current={view === "skills" ? "page" : undefined}
          >
            <span aria-hidden="true">↗</span> سجل المهارات
          </button>
        </nav>
        <div className="side-note">
          <span className="spark" aria-hidden="true">
            ✳
          </span>
          <h3>كل محاولة بتفرق.</h3>
          <p>
            هنا الغلط جزء من التعلّم.
            <br />
            جرّب، خد ملاحظات، وارجع أحسن.
          </p>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar small">
            {user?.display_name.slice(0, 1) || "؟"}
          </span>
          <div>
            {user?.display_name || "مكانك مستنيك"}
            <small>
              {user ? "متدرّب · فريق البيانات" : "ابدأ أول يوم شغل"}
            </small>
          </div>
          {user && (
            <button
              className="icon-button"
              aria-label="تسجيل الخروج"
              onClick={() => setLogoutOpen(true)}
            >
              ↪
            </button>
          )}
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <span>
            مساحة التعلّم <span className="slash">/</span>{" "}
            <strong>{view === "work" ? "مكتبي" : "سجل المهارات"}</strong>
          </span>
          <div className="top-actions">
            <span className="workspace-status">
              <i /> تجربة العمل
            </span>
            {user && (
              <button
                className="text-button"
                onClick={() => setLogoutOpen(true)}
              >
                إنهاء الجلسة
              </button>
            )}
          </div>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <p className="eyebrow">خطوة صغيرة. خبرة حقيقية.</p>
              <h1>
                {view === "skills"
                  ? "شوف أنت اتقدّمت إزاي."
                  : user
                    ? `أهلاً ${user.display_name}، يلا نشتغل.`
                    : "أول يوم ليك، بداية مختلفة."}
              </h1>
              <p>
                اتعلّم بالشغل، مش بالمشاهدة. كل مهمة خطوة أقرب للثقة في مهاراتك.
              </p>
            </div>
            <span className="day-chip">
              اليوم <b>01</b>
            </span>
          </div>
          {error && (
            <div
              className="error-banner"
              role="alert"
              tabIndex={-1}
              ref={errorHeading}
            >
              {error}
              <button onClick={() => setError("")} aria-label="إغلاق التنبيه">
                ×
              </button>
            </div>
          )}
          <div role="status" aria-live="polite" className="loading-status">
            {busy || (booting ? "بنفتح مساحة العمل…" : "")}
          </div>
          {!user ? (
            <div className="welcome-grid">
              <section className="welcome-card">
                <span className="section-tag">أهلاً بيك في الفريق</span>
                <h2>
                  مش محتاج خبرة
                  <br />
                  عشان تبدأ تكوّن خبرة.
                </h2>
                <p>
                  مهمتك الأولى مستنياك: ملف مبيعات محتاج ترتيب، ومدير يساعدك
                  تفهم أثر شغلك.
                </p>
                <div className="welcome-steps">
                  <span>
                    <b>01</b> استلم المهمة
                  </span>
                  <span>
                    <b>02</b> جرّب بإيدك
                  </span>
                  <span>
                    <b>03</b> اتعلّم من النتيجة
                  </span>
                </div>
              </section>
              <form className="join-card" onSubmit={begin}>
                <span className="avatar">أ</span>
                <h2>نبدأ نتعرف؟</h2>
                <p>اكتب الاسم اللي تحب نناديك بيه.</p>
                <label htmlFor="name">اسمك</label>
                <input
                  ref={nameInput}
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={80}
                  required
                  autoComplete="given-name"
                  placeholder="مثلاً: أحمد"
                />
                <button
                  className="primary"
                  disabled={!!busy || booting || !runtime || !name.trim()}
                >
                  ابدأ أول يوم <span aria-hidden="true">←</span>
                </button>
                <small>
                  من غير إيميل أو كلمة سر. خروجك أو مسح بيانات المتصفح هيخلّيك
                  تفقد الوصول للجلسة.
                </small>
                {!runtime && !booting && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => location.reload()}
                  >
                    حاول الاتصال تاني
                  </button>
                )}
              </form>
            </div>
          ) : view === "skills" ? (
            <section className="skills-view">
              <div className="section-heading">
                <h2>مهارات اتبنت بالممارسة</h2>
                <span className="muted">{history.length} محاولة مسجّلة</span>
              </div>
              {skills?.skills.length ? (
                <div className="skill-grid">
                  {skills.skills.map((skill) => (
                    <article className="skill-card" key={skill.skill_id}>
                      <span className="skill-icon" aria-hidden="true">
                        ↗
                      </span>
                      <h3>{skillNames[skill.skill_id] || skill.skill_id}</h3>
                      <strong>
                        <bdi>{skill.score}</bdi>
                        <small> / 100</small>
                      </strong>
                      <progress
                        value={skill.score}
                        max={100}
                        aria-label={
                          skillNames[skill.skill_id] || skill.skill_id
                        }
                      />
                      <p>مبني على الفحوصات المسجّلة للتسليمات المقبولة.</p>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <span aria-hidden="true">◇</span>
                  <h3>أول إنجاز لسه قدّامك.</h3>
                  <p>كمّل المهمة الأولى عشان تبدأ تبني سجل مهاراتك.</p>
                  <button className="secondary" onClick={() => setView("work")}>
                    ارجع لمكتبي ←
                  </button>
                </div>
              )}
            </section>
          ) : (
            <div className="work-grid">
              <div className="work-main">
                <section className="task-card">
                  <div className="section-heading">
                    <span className="section-tag">مهمتك الأولى</span>
                    <span className={completed ? "pill success" : "pill"}>
                      {completed ? "✓ مكتملة" : "جاري العمل"}
                    </span>
                  </div>
                  <h2>
                    وراء كل قرار صح،
                    <br />
                    بيانات تقدر تثق فيها.
                  </h2>
                  <p className="task-subtitle">
                    تنظيف بيانات المبيعات <span>·</span> فريق البيانات
                  </p>
                  <div className="manager-note">
                    <span className="avatar">ط</span>
                    <div>
                      <strong>
                        م. طارق <small>مدير فريق البيانات</small>
                      </strong>
                      <p>
                        صباح الخير يا بطل. معانا ملف مبيعات محتاج مراجعة قبل ما
                        نطلع التقرير. ركّز في التفاصيل، وخد وقتك.
                      </p>
                      <p>
                        {task?.task?.instructions_ar ||
                          "مفيش مهمة متاحة دلوقتي."}
                      </p>
                    </div>
                  </div>
                  <div className="checks-list">
                    <span>① راجع الطلبات المتكررة</span>
                    <span>② وحّد صيغة التواريخ</span>
                    <span>③ راجع القيم الرقمية</span>
                    <span>④ كمّل البيانات المطلوبة</span>
                  </div>
                  <div className="file-card">
                    <div className="file-icon">CSV</div>
                    <div>
                      <strong>
                        <bdi>sales_dirty.csv</bdi>
                      </strong>
                      <small>ملف المبيعات الخام · CSV أو Excel</small>
                    </div>
                    <button
                      className="secondary"
                      onClick={() => void download("csv")}
                    >
                      نزّل CSV <span aria-hidden="true">↓</span>
                    </button>
                    <button
                      className="secondary"
                      onClick={() => void download("xlsx")}
                    >
                      نزّل Excel <span aria-hidden="true">↓</span>
                    </button>
                  </div>
                </section>
                <section className="submission-card">
                  <div className="section-heading">
                    <h2>
                      {completed
                        ? "شغل يستاهل خطوة جديدة."
                        : "جاهز تسلّم شغلك؟"}
                    </h2>
                    <span className="muted">
                      {history.length
                        ? `المحاولة ${history.length + (completed ? 0 : 1)}`
                        : "المحاولة الأولى"}
                    </span>
                  </div>
                  {completed ? (
                    <p>المهمة اتقبلت. تقدر تراجع النتيجة وتشوف سجل مهاراتك.</p>
                  ) : (
                    <form onSubmit={submit}>
                      <label className="upload-zone" htmlFor="submission">
                        <span className="upload-icon" aria-hidden="true">
                          ↑
                        </span>
                        <strong>
                          {file ? (
                            <bdi>{file.name}</bdi>
                          ) : (
                            "اختار النسخة اللي اشتغلت عليها"
                          )}
                        </strong>
                        <span>CSV أو XLSX · حتى 5 ميجابايت</span>
                        <input
                          id="submission"
                          type="file"
                          accept=".csv,.xlsx"
                          disabled={!!busy || !!pending}
                          onChange={(e) => {
                            const next = e.target.files?.[0];
                            if (next) {
                              const invalid = validateFile(next);
                              setError(invalid || "");
                              setFile(invalid ? null : next);
                            }
                          }}
                        />
                      </label>
                      <div className="submission-actions">
                        <p>كل محاولة فرصة تفهم أكتر.</p>
                        <button
                          className="primary"
                          disabled={!!busy || (!file && !pending)}
                        >
                          {pending ? "تحقق من النتيجة" : "سلّم للمراجعة"}{" "}
                          <span aria-hidden="true">←</span>
                        </button>
                      </div>
                    </form>
                  )}
                </section>
                {outcome && (
                  <section
                    className="result-card"
                    aria-labelledby="result-heading"
                  >
                    <div className="section-heading">
                      <h2 id="result-heading" tabIndex={-1} ref={resultHeading}>
                        {outcome.evaluation.passed
                          ? "تمام، التسليم اتقبل!"
                          : "قربت، محتاجين نراجع كام حاجة."}
                      </h2>
                      <strong className="score">
                        <bdi>{outcome.evaluation.score}/100</bdi>
                      </strong>
                    </div>
                    <p className="eyebrow">نتيجة الفحوصات الحتمية</p>
                    <ul className="result-checks">
                      {outcome.evaluation.checks.map((check) => (
                        <li key={check.check_id}>
                          <span
                            className={check.passed ? "pass-icon" : "fail-icon"}
                          >
                            {check.passed ? "✓ نجح" : "! يحتاج مراجعة"}
                          </span>
                          {check.details_ar}
                        </li>
                      ))}
                    </ul>
                    <div className="coach-note">
                      <strong>
                        {outcome.feedback.used_fallback
                          ? "إرشادات بديلة · من غير اتصال بالذكاء الاصطناعي"
                          : "ملاحظات المدرب · مولّدة بالذكاء الاصطناعي"}
                      </strong>
                      <p>{outcome.feedback.feedback_text}</p>
                    </div>
                  </section>
                )}
              </div>
              <aside className="context-column">
                <section className="progress-card">
                  <span className="section-tag">رحلتك النهارده</span>
                  <h3>
                    خبرة بتتبني،
                    <br />
                    خطوة بخطوة.
                  </h3>
                  <ol className="timeline">
                    <li className="done">
                      <b>✓</b>
                      <div>
                        انضمّيت للفريق<small>أهلاً بيك في يوم أول</small>
                      </div>
                    </li>
                    <li className={completed ? "done" : "current"}>
                      <b>{completed ? "✓" : "2"}</b>
                      <div>
                        اشتغل على أول مهمة<small>راجع، جرّب، وسلّم</small>
                      </div>
                    </li>
                    <li className={completed ? "done" : ""}>
                      <b>{completed ? "✓" : "3"}</b>
                      <div>
                        سجّل أول إنجاز<small>شوف مهاراتك وهي بتكبر</small>
                      </div>
                    </li>
                  </ol>
                  <button
                    className="text-button"
                    onClick={() => setView("skills")}
                  >
                    شوف سجل مهاراتك ←
                  </button>
                </section>
                <section className="tip-card">
                  <span aria-hidden="true">✳</span>
                  <h3>قبل ما تدوس تسليم</h3>
                  <p>
                    بص على الملف كأنك زميلك اللي هيستخدمه. الأرقام واضحة؟
                    التواريخ مفهومة؟ كل تفصيلة صغيرة بتفرق.
                  </p>
                </section>
                <section className="history-card">
                  <h3>محاولاتك السابقة</h3>
                  {history.length ? (
                    history
                      .slice()
                      .reverse()
                      .map((item) => (
                        <div className="history-row" key={item.submission_id}>
                          <span>
                            محاولة {item.attempt_number}
                            <small>
                              {item.evaluation.passed
                                ? "مقبولة"
                                : "تحتاج مراجعة"}
                            </small>
                          </span>
                          <bdi>{item.evaluation.score}/100</bdi>
                        </div>
                      ))
                  ) : (
                    <p className="muted">
                      لسه مفيش تسليمات.
                      <br />
                      أول محاولة هي البداية.
                    </p>
                  )}
                </section>
              </aside>
            </div>
          )}
          <footer>
            يوم أول <span>·</span> مساحة آمنة تتعلّم فيها بالشغل.
          </footer>
        </main>
      </div>
      {logoutOpen && (
        <div className="dialog-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="logout-title"
            className="logout-dialog"
            onKeyDown={(e) => {
              if (e.key === "Escape") setLogoutOpen(false);
              if (e.key === "Tab") {
                const buttons =
                  e.currentTarget.querySelectorAll<HTMLButtonElement>("button");
                const first = buttons[0],
                  last = buttons[buttons.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                  e.preventDefault();
                  last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                  e.preventDefault();
                  first.focus();
                }
              }
            }}
          >
            <h2 id="logout-title">متأكد إنك عايز تخرج؟</h2>
            <p>
              دي جلسة من غير حساب. تسجيل الخروج هيخلّيك تفقد الوصول لتقدّمك، ومش
              هنقدر نرجّعه.
            </p>
            <div>
              <button
                className="secondary"
                autoFocus
                onClick={() => setLogoutOpen(false)}
              >
                خلّيني هنا
              </button>
              <button className="primary" onClick={() => void logout()}>
                تسجيل الخروج وفقد الوصول
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
