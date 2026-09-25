"use client";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { dictionaries, LANG_COOKIE } from "./dictionaries";
import type { Dictionary } from "./en";
import { directionOf, type Lang } from "./keys";

type LanguageState = {
  lang: Lang;
  t: Dictionary;
  setLang: (lang: Lang) => void;
};
const LanguageContext = createContext<LanguageState | null>(null);

export function applyDocumentLanguage(lang: Lang) {
  document.documentElement.lang = lang;
  document.documentElement.dir = directionOf(lang);
  document.title = dictionaries[lang].meta.title;
  document.cookie = `${LANG_COOKIE}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

export function LanguageProvider({
  initialLang,
  children,
}: {
  initialLang: Lang;
  children: React.ReactNode;
}) {
  const [lang, setState] = useState(initialLang);
  const setLang = useCallback((next: Lang) => {
    applyDocumentLanguage(next);
    setState(next);
  }, []);
  const value = useMemo(
    () => ({ lang, t: dictionaries[lang], setLang }),
    [lang, setLang],
  );
  return <LanguageContext value={value}>{children}</LanguageContext>;
}

export function useLanguage(): LanguageState {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside LanguageProvider");
  return value;
}
