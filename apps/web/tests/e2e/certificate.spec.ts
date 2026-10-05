import { expect, test } from "@playwright/test";
import { copy, demoFile, expectAccessible, expectNoHorizontalScroll, onboard, openCleanSales, shot, submitFile } from "./flow";

test("a passed task earns a certificate an employer can verify without signing in", async ({ page, browser }) => {
  const t = copy.en;
  await onboard(page, "Sara Ahmed", "en");
  await page.getByRole("button", { name: t.shell.nav.skills }).first().click();
  await expect(page.getByText(t.certificate.locked)).toBeVisible();

  await page.getByRole("button", { name: t.shell.nav.tasks }).first().click();
  await openCleanSales(page, "en");
  await submitFile(page, "en", demoFile("sales_retry_duplicates.csv"));
  await submitFile(page, "en", demoFile("sales_cleaned.xlsx"));
  await page.getByRole("button", { name: t.result.viewSkills }).click();

  const card = page.getByRole("region", { name: t.certificate.title });
  await expect(card.getByRole("img", { name: t.certificate.qr("Sara Ahmed") })).toBeVisible();
  const url = await card.getByLabel(t.certificate.link).inputValue();
  expect(url).toMatch(/\/verify\/[A-Za-z0-9_-]{43}\?lang=en$/);
  await expectAccessible(page);
  await card.screenshot({ path: shot("certificate-card-en") });

  const employer = await browser.newContext();
  const verify = await employer.newPage();
  await verify.goto(url);
  await expect(verify.getByRole("heading", { level: 1, name: t.certificate.title })).toBeVisible();
  await expect(verify.getByText("Sara Ahmed")).toBeVisible();
  await expect(verify.locator(".certificate-tasks li")).toContainText(t.certificate.attempts(2));
  await expect(verify.locator(".certificate-tasks li")).toContainText("100/100");
  await expect(verify.getByText(t.skills.names.data_cleaning)).toBeVisible();
  expect((await employer.cookies()).some((cookie) => cookie.name === "yom_session")).toBe(false);
  await expectAccessible(verify);
  await verify.screenshot({ path: shot("certificate-verify-en"), fullPage: true });

  const token = new URL(url).pathname.split("/").pop()!;
  const edited = token.slice(0, 10) + (token[10] === "A" ? "B" : "A") + token.slice(11);
  await verify.goto(url.replace(token, edited));
  await expect(verify.getByRole("heading", { level: 1, name: t.certificate.invalidTitle })).toBeVisible();
  await employer.close();
});

test("Arabic verify page on a 390px phone", async ({ page, browser }) => {
  await onboard(page, "مريم", "ar");
  await openCleanSales(page, "ar");
  await submitFile(page, "ar", demoFile("sales_cleaned.csv"));
  const certificate = await (await page.request.get("/api/v1/learners/me/certificate")).json();

  const employer = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const verify = await employer.newPage();
  await verify.goto(`/verify/${certificate.token}`);
  await expect(verify.getByRole("heading", { level: 1, name: copy.ar.certificate.title })).toBeVisible();
  await expect(verify.getByText(copy.ar.certificate.attempts(1))).toBeVisible();
  await expectNoHorizontalScroll(verify);
  await expectAccessible(verify);
  await verify.screenshot({ path: shot("certificate-verify-ar-mobile"), fullPage: true });
  await employer.close();
});
