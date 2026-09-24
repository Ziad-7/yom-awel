import { useLanguage } from "../lib/i18n/language";

/** Keeps focus inside the modal while it is open. */
function trapFocus(event: React.KeyboardEvent<HTMLElement>, close: () => void) {
  if (event.key === "Escape") close();
  if (event.key !== "Tab") return;
  const buttons = event.currentTarget.querySelectorAll<HTMLButtonElement>("button");
  const first = buttons[0];
  const last = buttons[buttons.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

export function RestartDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="dialog-backdrop">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="restart-title"
        aria-describedby="restart-body"
        className="restart-dialog"
        onKeyDown={(event) => trapFocus(event, onCancel)}
      >
        <h2 id="restart-title">{t.restart.title}</h2>
        <p id="restart-body">{t.restart.body}</p>
        <div>
          <button type="button" className="secondary" autoFocus onClick={onCancel}>
            {t.restart.cancel}
          </button>
          <button type="button" className="danger" onClick={onConfirm}>
            {t.restart.confirm}
          </button>
        </div>
      </section>
    </div>
  );
}
