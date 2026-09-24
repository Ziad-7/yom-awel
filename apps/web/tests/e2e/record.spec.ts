import { test } from "@playwright/test";
import { demoJourney } from "./journey";

test.describe.configure({ timeout: 240000 });

test("demo video: Arabic with CSV", async ({ page }) => {
  await demoJourney(page, "ar", { format: "csv", audit: false, pause: 1500 });
});

test("demo video: English with XLSX", async ({ page }) => {
  await demoJourney(page, "en", { format: "xlsx", audit: false, pause: 1500 });
});
