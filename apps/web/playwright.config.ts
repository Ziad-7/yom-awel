import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8000;
const WEB_PORT = 3000;
// Containers with a preinstalled browser point PLAYWRIGHT_CHROMIUM_EXECUTABLE at it instead of downloading.
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
const chromium = executablePath
  ? { ...devices["Desktop Chrome"], launchOptions: { executablePath } }
  : { ...devices["Desktop Chrome"], channel: "chromium" };

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [
    // Browser flows against the typed contract mock: no API process involved.
    { name: "mock", testMatch: /mock-flow\.spec\.ts/, use: chromium },
    // The full demo against uvicorn, the real evaluator and Lane D's presenter files.
    { name: "real", testMatch: /demo-flow\.spec\.ts/, use: chromium },
    // `npm run demo:record`: the whole flow in Arabic then English, on video.
    {
      name: "record",
      testMatch: /record\.spec\.ts/,
      outputDir: "demo-video",
      use: { ...chromium, video: { mode: "on", size: { width: 1280, height: 800 } }, viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: [
    {
      command: `uv run --project ../../services/api uvicorn yom_awel.transport.app:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        APP_ENV: "local",
        FEEDBACK_MODE: "fallback",
        LOCAL_DATABASE_PATH: ".local/e2e.sqlite3",
        CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT}`,
      },
    },
    {
      command: `npm run dev -- --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: { API_ORIGIN: `http://127.0.0.1:${API_PORT}`, NEXT_TELEMETRY_DISABLED: "1" },
    },
  ],
});
