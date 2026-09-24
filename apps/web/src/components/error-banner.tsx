import { useEffect, useRef } from "react";
import { useLanguage } from "../lib/i18n/language";

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  const { t } = useLanguage();
  const banner = useRef<HTMLDivElement>(null);
  useEffect(() => banner.current?.focus(), [message]);
  return (
    <div className="error-banner" role="alert" tabIndex={-1} ref={banner}>
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label={t.errors.dismiss}>
        ×
      </button>
    </div>
  );
}
