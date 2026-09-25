import { expect, type Page } from "@playwright/test";
import type { Lang } from "../../src/lib/i18n/keys";
import {
  copy,
  demoFile,
  expectAccessible,
  expectDocumentLanguage,
  onboard,
  openCleanSales,
  shot,
  submitFile,
  toggleFeedback,
} from "./flow";

type Format = "csv" | "xlsx";
type JourneyOptions = { format: Format; audit: boolean; pause: number };

const RETRY_FILE: Record<Format, string> = { csv: "sales_retry_duplicates.csv", xlsx: "sales_retry_half.xlsx" };
const CLEAN_FILE: Record<Format, string> = { csv: "sales_cleaned.csv", xlsx: "sales_cleaned.xlsx" };

async function checkpoint(page: Page, name: string, options: JourneyOptions) {
  if (options.audit) {
    await expectAccessible(page);
    await page.screenshot({ path: shot(name), fullPage: true });
  }
  if (options.pause) await page.waitForTimeout(options.pause);
}

/** The full demo against the real API: onboard, download, reject, retry, pass, progress. */
export async function demoJourney(page: Page, lang: Lang, options: JourneyOptions) {
  const t = copy[lang];
  const other: Lang = lang === "ar" ? "en" : "ar";
  await onboard(page, lang === "ar" ? "نور الدين" : "Noor", lang);
  await checkpoint(page, `${lang}-catalogue`, options);
  await openCleanSales(page, lang);
  await checkpoint(page, `${lang}-workspace`, options);

  for (const format of ["csv", "xlsx"] as const) {
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: format === "csv" ? t.workspace.downloadCsv : t.workspace.downloadXlsx }).click();
    expect((await download).suggestedFilename()).toBe(`sales_dirty.${format}`);
  }

  await submitFile(page, lang, demoFile("sales_rejected_missing_columns.csv"));
  await expect(page.locator("#result-heading")).toHaveText(t.result.rejectedTitle);
  await expect(page.getByText(t.rejections.missing_columns)).toBeVisible();
  await checkpoint(page, `${lang}-rejected`, options);

  await submitFile(page, lang, demoFile(RETRY_FILE[options.format]));
  await expect(page.locator("#result-heading")).toHaveText(t.result.failTitle);
  if (options.format === "csv") await expect(page.getByText(t.result.criticalFailed(75, 75))).toBeVisible();
  else await expect(page.getByText(t.result.failure(50))).toBeVisible();
  await checkpoint(page, `${lang}-${options.format}-retry`, options);
  await toggleFeedback(page, lang);
  await checkpoint(page, `${lang}-feedback-in-${other}`, options);

  await page.getByRole("button", { name: t.result.uploadRevision }).click();
  await submitFile(page, lang, demoFile(CLEAN_FILE[options.format]));
  await expect(page.locator("#result-heading")).toHaveText(t.result.passTitle);
  await expect(page.getByText(t.result.success(100))).toBeVisible();
  await expect(page.locator(".result-checks .pass-icon")).toHaveCount(4);
  await checkpoint(page, `${lang}-${options.format}-pass`, options);

  await page.getByRole("button", { name: t.result.viewSkills }).click();
  await expect(page.getByRole("progressbar", { name: t.skills.names.data_cleaning })).toBeVisible();
  await expect(page.locator(".attempt-timeline li")).toHaveCount(3);
  await expect(page.locator(".status-list")).toContainText(t.catalogue.status.completed);
  await checkpoint(page, `${lang}-skills`, options);
  await expectDocumentLanguage(page, lang);
}
