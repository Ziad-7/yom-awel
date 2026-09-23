import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const dirty =
  "order_id,date,quantity,revenue,customer_email\n1,2026/09/01,-2,100,\n1,2026/09/01,-2,100,\n";
const clean =
  "order_id,date,quantity,revenue,customer_email\n1,2026-09-01,2,100,customer@example.test\n";

test("Arabic onboarding, failure, retry, pass, reload and skills", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await page.getByLabel("اسمك", { exact: true }).fill("سارة");
  await page.getByRole("button", { name: "ابدأ أول يوم" }).click();
  await expect(
    page.getByRole("heading", { name: "أهلاً سارة، يلا نشتغل." }),
  ).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({
    path: "test-results/member5-desktop.png",
    fullPage: true,
  });
  await page.locator("#submission").setInputFiles({
    name: "dirty.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(dirty),
  });
  await page.getByRole("button", { name: "سلّم للمراجعة" }).click();
  await expect(page.locator("#result-heading")).toContainText("قربت");
  await expect(page.locator("#result-heading")).toBeFocused();
  await expect(
    page.getByText("إرشادات بديلة · من غير اتصال بالذكاء الاصطناعي"),
  ).toBeVisible();
  await page.locator("#submission").setInputFiles({
    name: "clean.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(clean),
  });
  await page.getByRole("button", { name: "سلّم للمراجعة" }).click();
  await expect(page.locator("#result-heading")).toContainText("التسليم اتقبل");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "أهلاً سارة، يلا نشتغل." }),
  ).toBeVisible();
  await expect(page.getByText("✓ مكتملة")).toBeVisible();
  await page
    .getByRole("button", { name: "سجل المهارات", exact: false })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "تنظيف البيانات" }),
  ).toBeVisible();
  await expect(page.getByRole("progressbar")).toHaveAttribute("value", "100");
  await page.getByRole("button", { name: "إنهاء الجلسة" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("button", { name: "خلّيني هنا" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page.getByRole("button", { name: "تسجيل الخروج وفقد الوصول" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "تسجيل الخروج وفقد الوصول" }).click();
  await expect(page.getByLabel("اسمك", { exact: true })).toBeVisible();
});

test("mobile layout, keyboard entry and invalid upload", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "انتقل للمحتوى" })).toBeFocused();
  await page.getByLabel("اسمك", { exact: true }).fill("عمر");
  await page.getByLabel("اسمك", { exact: true }).press("Enter");
  await expect(page.locator("#submission")).toBeVisible();
  await page.locator("#submission").setInputFiles({
    name: "bad.exe",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("x"),
  });
  await expect(
    page.getByRole("alert").filter({ hasText: "CSV أو XLSX" }),
  ).toContainText("CSV أو XLSX");
  await expect(
    page.getByRole("alert").filter({ hasText: "CSV أو XLSX" }),
  ).toBeFocused();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: "test-results/member5-mobile.png",
    fullPage: true,
  });
});
