import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import { createMockApi, evaluation } from "../test/mock-api";
import Workplace from "./workplace";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  document.cookie = "yom_lang=; Max-Age=0; Path=/";
});

function mount(outcome = evaluation(), lang: Lang = "ar") {
  const api = createMockApi(outcome);
  vi.stubGlobal("fetch", vi.fn(api.fetch));
  render(
    <LanguageProvider initialLang={lang}>
      <Workplace />
    </LanguageProvider>,
  );
  return api;
}

async function onboardAndOpen(name: string) {
  fireEvent.change(await screen.findByRole("textbox"), { target: { value: name } });
  fireEvent.click(screen.getByRole("button", { name: /ابدأ أول يوم عمل|Start my first workday/ }));
  fireEvent.click(await screen.findByRole("button", { name: /ابدأ المهمة|Start task/ }));
  await screen.findByRole("heading", { level: 2, name: /المطلوب|How you'll be graded|هتتقيّم/ });
}

async function upload(name: string, content: string) {
  const file = new File([content], name, { type: "text/csv" });
  fireEvent.change(document.getElementById("submission")!, { target: { files: [file] } });
  const submit = await screen.findByRole("button", { name: /سلّم للمراجعة|Submit for review/ });
  await waitFor(() => expect(submit).toBeEnabled());
  fireEvent.click(submit);
}

describe("Workplace against the typed contract mock", () => {
  it("onboards in Arabic, passes, and toggles feedback to English", async () => {
    const api = mount();
    await onboardAndOpen("سارة");
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeInTheDocument();
    await upload("sales_cleaned.csv", "order_id\n1\n");
    const heading = await screen.findByRole("heading", { name: /تسلم إيدك/ });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(screen.getAllByText("25 من 25")).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: "Show in English" }));
    const english = await screen.findByText(/Decision: resubmit\./);
    expect(english).toHaveAttribute("dir", "ltr");
    expect(screen.getAllByText(/Eng\. Tarek, Team Lead/)).toHaveLength(1);
    expect(screen.getByRole("button", { name: "اعرض بالعربي" })).toBeInTheDocument();
    const posts = api.calls.filter((call) => call.method !== "GET");
    expect(posts.every((call) => call.headers["x-yom-awel"] === "1")).toBe(true);
    expect(api.calls.every((call) => call.path.startsWith("/api/v1/"))).toBe(true);
    const submission = api.calls.find((call) => call.path === "/api/v1/submissions");
    expect(submission?.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(api.calls.some((call) => call.path.includes("feedback?language=en"))).toBe(true);
  });

  it("explains a 75 score that fails the critical check, in English", async () => {
    mount(evaluation(["unique_orders"]), "en");
    await onboardAndOpen("Sara");
    await upload("sales_retry_duplicates.csv", "order_id\n1\n");
    expect(await screen.findByText(/critical “Unique orders” check failed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Upload revision/ })).toBeInTheDocument();
    expect(screen.getByText("0 of 25")).toBeInTheDocument();
  });

  it("shows the rejection message for an evaluator rejection code", async () => {
    mount(evaluation([], ["too_few_rows"]), "en");
    await onboardAndOpen("Sara");
    await upload("tiny.csv", "order_id\n1\n");
    expect(await screen.findByText(/Fewer than 40 data rows remain/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /rejected before grading/ })).toBeInTheDocument();
  });

  it("rejects an unsupported file before any upload", async () => {
    const api = mount(evaluation(), "en");
    await onboardAndOpen("Sara");
    const file = new File(["x"], "notes.pdf", { type: "application/pdf" });
    fireEvent.change(document.getElementById("submission")!, { target: { files: [file] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/Unsupported file type/);
    expect(api.calls.some((call) => call.path.includes("upload-authorization"))).toBe(false);
  });

  it("switches language before onboarding without calling the API, and after it with PUT", async () => {
    const api = mount();
    const toggle = await screen.findByRole("button", { name: "Switch to English" });
    fireEvent.click(toggle);
    expect(document.documentElement).toHaveAttribute("lang", "en");
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
    expect(api.calls.some((call) => call.path.endsWith("/language"))).toBe(false);
    await onboardAndOpen("Sara");
    fireEvent.click(screen.getByRole("button", { name: "التحويل إلى العربية" }));
    await waitFor(() =>
      expect(api.calls.find((call) => call.path === "/api/v1/learners/me/language")?.body).toEqual({
        preferred_language: "ar-EG",
      }),
    );
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    const nav = screen.getByRole("navigation");
    expect(within(nav).getByRole("button", { name: /المهام/ })).toBeInTheDocument();
  });
});
