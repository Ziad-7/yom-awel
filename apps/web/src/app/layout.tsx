import type { Metadata } from "next";
import { cookies } from "next/headers";
import { SkipLink } from "../components/skip-link";
import { dictionaries, LANG_COOKIE } from "../lib/i18n/dictionaries";
import { LanguageProvider } from "../lib/i18n/language";
import { directionOf, isLang, type Lang } from "../lib/i18n/keys";
import "./globals.css";

async function requestLang(): Promise<Lang> {
  const value = (await cookies()).get(LANG_COOKIE)?.value;
  return isLang(value) ? value : "ar";
}

export async function generateMetadata(): Promise<Metadata> {
  const { meta } = dictionaries[await requestLang()];
  return { title: meta.title, description: meta.description };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const lang = await requestLang();
  return (
    <html lang={lang} dir={directionOf(lang)}>
      <body>
        <LanguageProvider initialLang={lang}>
          <SkipLink />
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
