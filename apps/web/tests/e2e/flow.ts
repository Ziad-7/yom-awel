import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import path from "node:path";
import { ar } from "../../src/lib/i18n/ar";
import { en } from "../../src/lib/i18n/en";
import type { Lang } from "../../src/lib/i18n/keys";

export const copy = { ar, en } as const;
export const demoFile = (name: string) => path.resolve(__dirname, "../../../../demo/files", name);
export const shot = (name: string) => `test-results/screens/${name}.png`;

export async function expectAccessible(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
}

export async function expectNoHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

export async function expectDocumentLanguage(page: Page, lang: Lang) {
  await expect(page.locator("html")).toHaveAttribute("lang", lang);
  await expect(page.locator("html")).toHaveAttribute("dir", lang === "ar" ? "rtl" : "ltr");
}

/** Onboards a fresh learner; English is chosen on the onboarding form itself. */
export async function onboard(page: Page, name: string, lang: Lang) {
  await page.goto("/");
  await expectDocumentLanguage(page, "ar");
  if (lang === "en") await page.getByLabel("English", { exact: true }).check();
  const t = copy[lang];
  await expectDocumentLanguage(page, lang);
  await page.getByLabel(t.onboarding.nameLabel, { exact: true }).fill(name);
  await page.getByRole("button", { name: t.onboarding.submit }).click();
  await expect(page.getByRole("heading", { level: 1, name: t.headings.greeting(name) })).toBeVisible();
}

export async function openCleanSales(page: Page, lang: Lang) {
  const t = copy[lang];
  await page.getByRole("button", { name: new RegExp(t.catalogue.action.available) }).click();
  await expect(page.getByRole("heading", { name: t.workspace.checks })).toBeVisible();
}

type Upload = string | { name: string; mimeType: string; buffer: Buffer };

export async function submitFile(page: Page, lang: Lang, file: Upload) {
  const t = copy[lang];
  await page.locator("#submission").setInputFiles(file);
  await page.getByRole("button", { name: t.upload.submit }).click();
  await expect(page.locator("#result-heading")).toBeFocused();
}

export async function toggleFeedback(page: Page, from: Lang) {
  const card = page.locator(".feedback-card");
  await card.getByRole("button", { name: copy[from].feedback.toggle }).click();
  const other: Lang = from === "ar" ? "en" : "ar";
  await expect(card.locator(".feedback-text")).toHaveAttribute("lang", other);
  await expect(card.locator(".feedback-text")).toHaveAttribute("dir", other === "ar" ? "rtl" : "ltr");
  await expect(card.getByRole("button", { name: copy[other].feedback.toggle })).toBeVisible();
}
