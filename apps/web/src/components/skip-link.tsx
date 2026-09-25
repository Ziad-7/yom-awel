"use client";
import { useLanguage } from "../lib/i18n/language";

export function SkipLink() {
  const { t } = useLanguage();
  return (
    <a className="skip" href="#main">
      {t.shell.skip}
    </a>
  );
}
