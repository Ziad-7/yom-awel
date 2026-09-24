import { useLanguage } from "../lib/i18n/language";
import { TarekAvatar } from "./persona";

export function ProcessingState({ message }: { message: string }) {
  const { t } = useLanguage();
  return (
    <section className="card processing" aria-labelledby="processing-title" aria-busy="true">
      <div className="processing-head">
        <TarekAvatar />
        <div>
          <h2 id="processing-title">{t.processing.title}</h2>
          <p>{message}</p>
        </div>
      </div>
      <ol className="processing-steps">
        {t.processing.steps.map((step) => (
          <li key={step}>
            <span className="pulse" aria-hidden="true" />
            {step}
          </li>
        ))}
      </ol>
    </section>
  );
}
