import { defineConfig } from "@playwright/test";
import localConfig from "./playwright.config";

const hostedWebUrl = process.env.HOSTED_WEB_URL;
const hostedUrl = hostedWebUrl && URL.canParse(hostedWebUrl) ? new URL(hostedWebUrl) : null;
if (
  !hostedUrl ||
  hostedUrl.protocol !== "https:" ||
  hostedUrl.pathname !== "/" ||
  hostedUrl.search ||
  hostedUrl.hash ||
  hostedUrl.username ||
  hostedUrl.password
) {
  throw new Error("HOSTED_WEB_URL must be the HTTPS origin of an isolated web preview");
}

export default defineConfig({
  ...localConfig,
  use: { ...localConfig.use, baseURL: hostedUrl.origin },
  projects: localConfig.projects?.filter((project) => project.name === "real"),
  webServer: [],
});
