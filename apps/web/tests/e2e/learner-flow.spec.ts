import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// The learner's real dirty file, and its cleaned version rebuilt by the task generator.
const dirty = readFileSync(
  "../../task_packages/clean-sales/1/data/sales_dirty.csv",
);
const clean = execFileSync("uv", [
  "run",
  "--project",
  "../../services/api",
  "python",
  "-c",
  "import sys; from yom_awel.evaluation.clean_sales_dataset import LEARNER_SEED, generate, to_csv; sys.stdout.write(to_csv(generate(LEARNER_SEED).clean))",
]);

test("Arabic onboarding, failure, retry, pass, reload and skills", async ({
  page,
}) => {
  const response = await page.goto("/");
  expect(response).not.toBeNull();
  expect(response!.headers()["content-security-policy"]).toBe(
    "frame-ancestors 'none'",
  );
  expect(response!.headers()["x-frame-options"]).toBe("DENY");
  expect(response!.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response!.headers()["referrer-policy"]).toBe(
    "strict-origin-when-cross-origin",
  );
  expect(response!.headers()["permissions-policy"]).toBe(
    "camera=(), microphone=(), geolocation=(), browsing-topics=()",
  );
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
    buffer: dirty,
  });
  await page.getByRole("button", { name: "سلّم للمراجعة" }).click();
  await expect(page.locator("#result-heading")).toContainText("قربت");
  await expect(page.locator("#result-heading")).toBeFocused();
  await expect(
    page.getByText("إرشادات بديلة · من غير اتصال بالذكاء الاصطناعي"),
  ).toBeVisible();
  const coaching = page.locator(".coach-note");
  for (const section of [
    "القرار:",
    "تأثير الشغل:",
    "الخطوة الجاية:",
    "تفسير الدرجة:",
  ]) {
    await expect(coaching).toContainText(section);
  }
  await expect(coaching).toContainText("التسليم محتاج إعادة شغل");
  await expect(coaching).toContainText("0 من 100");
  await expect(coaching).not.toContainText("Fallback message");
  await page.screenshot({
    path: "test-results/member5-failure-feedback.png",
    fullPage: true,
  });
  await page.locator("#submission").setInputFiles({
    name: "clean.csv",
    mimeType: "text/csv",
    buffer: clean,
  });
  await page.getByRole("button", { name: "سلّم للمراجعة" }).click();
  await expect(page.locator("#result-heading")).toContainText("التسليم اتقبل");
  await expect(coaching).toContainText("التسليم مقبول");
  await expect(coaching).toContainText("100 من 100");
  for (const section of [
    "القرار:",
    "تأثير الشغل:",
    "الخطوة الجاية:",
    "تفسير الدرجة:",
  ]) {
    await expect(coaching).toContainText(section);
  }
  await expect(coaching).toContainText("إرشادات بديلة");
  await page.screenshot({
    path: "test-results/member5-success-feedback.png",
    fullPage: true,
  });
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
