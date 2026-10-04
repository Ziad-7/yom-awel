import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SubmissionInsights } from "../lib/api/contract";
import { LanguageProvider } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import { evaluation, insightsFor } from "../test/mock-api";
import { InsightsPanel } from "./insights-panel";

const SUBMISSION = "00000000-0000-4000-8000-00000000000b";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function mount(responses: Array<SubmissionInsights | number>, lang: Lang = "en") {
  const paths: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      paths.push(String(input));
      const next = responses.length > 1 ? responses.shift()! : responses[0];
      return typeof next === "number"
        ? new Response(JSON.stringify({ code: "unavailable" }), { status: next })
        : new Response(JSON.stringify(next), { status: 200, headers: { "Content-Type": "application/json" } });
    }),
  );
  const view = render(
    <LanguageProvider initialLang={lang}>
      <InsightsPanel submissionId={SUBMISSION} />
    </LanguageProvider>,
  );
  return { paths, view };
}

const sql = (overrides: Partial<NonNullable<SubmissionInsights["sql"]>> = {}): SubmissionInsights => ({
  kind: "sql",
  task_id: "sql-report",
  rejected_code: null,
  checks: [
    { check_id: "report_columns", passed: true, issue_count: 0 },
    { check_id: "paid_regions", passed: false, issue_count: 1 },
    { check_id: "paid_order_counts", passed: false, issue_count: 2 },
    { check_id: "paid_revenue", passed: true, issue_count: 0 },
  ],
  impact: [{ metric_id: "regions_misreported", unit: "regions", value: "2" }],
  issues: [],
  sql: {
    columns: ["region", "paid_orders", "total_revenue"],
    columns_ok: true,
    rows: [
      { cells: ["Alexandria", "4", "230.00"], region_status: "ok", count_ok: false, revenue_ok: true },
      { cells: ["Narnia", "1", "10.00"], region_status: "unexpected", count_ok: false, revenue_ok: false },
    ],
    missing_regions: 1,
    robustness_failed: false,
    ...overrides,
  },
});

const EMAIL_TEXT = "To: salma@example.com\nSubject: Order YA-2048\n\nDear Salma,\nWe are sorry.\nBest regards,\nYom Awel";
const email: SubmissionInsights = {
  kind: "email",
  task_id: "client-email",
  rejected_code: null,
  checks: [
    { check_id: "recipient_and_subject", passed: true, issue_count: 0 },
    { check_id: "action_plan", passed: false, issue_count: 1 },
  ],
  impact: [{ metric_id: "customer_questions_left_open", unit: "elements", value: "1" }],
  issues: [],
  email: {
    text: EMAIL_TEXT,
    elements: [
      { element_id: "recipient", check_id: "recipient_and_subject", found: true, start: 0, end: 21 },
      { element_id: "apology", check_id: "action_plan", found: true, start: 65, end: 70 },
      { element_id: "refund", check_id: "action_plan", found: false, start: null, end: null },
    ],
    word_count: 14,
    min_words: 80,
    max_words: 250,
  },
};

describe("InsightsPanel", () => {
  it("prices the mistakes and highlights the exact cells in the learner's file", async () => {
    const { paths } = mount([insightsFor(evaluation(["unique_orders", "standard_dates"]))]);

    const impact = await screen.findByRole("region", { name: "What this would cost the business" });
    expect(within(impact).getByText("Revenue inflated by duplicate orders").parentElement).toHaveTextContent(/EGP\s?200/);
    expect(paths).toEqual([`/api/v1/submissions/${SUBMISSION}/insights`]);
    expect(screen.getByText("3 cells need attention across 3 rows.")).toBeInTheDocument();

    const table = screen.getByRole("table");
    const duplicate = within(table).getByRole("rowheader", { name: "2" }).closest("tr")!;
    expect(duplicate).toHaveTextContent("Duplicate order ID (same as row 4)");
    expect(within(duplicate).getAllByRole("cell").find((cell) => cell.className === "flagged")).toHaveTextContent("SO-1");
    expect(within(table).queryByRole("rowheader", { name: "3" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Standard dates/ }));
    expect(screen.getByRole("button", { name: /Standard dates/ })).toHaveAttribute("aria-pressed", "true");
    expect(within(table).getAllByRole("rowheader").map((cell) => cell.textContent)).toEqual(["5"]);

    fireEvent.click(screen.getByRole("checkbox", { name: "Only rows with issues" }));
    expect(within(table).getAllByRole("rowheader")).toHaveLength(6);
  });

  it("celebrates a clean file in Arabic without a table", async () => {
    mount([insightsFor(evaluation())], "ar");
    expect(await screen.findByText(/مفيش حاجة عدّت/)).toBeInTheDocument();
    expect(screen.getByText("كل الصفوف عدّت من كل الفحوصات.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("marks each SQL row without revealing the expected numbers", async () => {
    mount([sql()]);
    const table = await screen.findByRole("table");
    const alexandria = within(table).getByText("Alexandria").closest("tr")!;
    expect(alexandria).toHaveTextContent("Paid region");
    expect(alexandria).toHaveTextContent("Count wrong");
    expect(alexandria).toHaveTextContent("Revenue correct");
    expect(within(table).getByText("Narnia").closest("tr")).toHaveTextContent("Not a paid region");
    expect(screen.getByText("1 paid region is missing from your result.")).toBeInTheDocument();
    expect(screen.queryByText("Hard-coded numbers detected")).toBeNull();
  });

  it("calls out hard-coded SQL numbers", async () => {
    mount([sql({ robustness_failed: true, missing_regions: 0 })]);
    expect(await screen.findByRole("note")).toHaveTextContent(/Hard-coded numbers detected/);
  });

  it("highlights what the reviewer found in the email and lists what is missing", async () => {
    mount([email]);
    const apology = await screen.findByRole("button", { name: /Found: An apology/ });
    expect(screen.getByText("sorry").tagName).toBe("MARK");
    fireEvent.click(apology);
    expect(apology).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("sorry")).toHaveClass("active");
    expect(screen.getByText(/Missing:/).parentElement).toHaveTextContent("The refund explained");
    expect(screen.getByLabelText("14 words. Aim for 80 to 250.")).toHaveAttribute("value", "14");
  });

  it("recovers from a failed load and hides itself for rejected files", async () => {
    mount([503, { ...insightsFor(evaluation([], ["too_few_rows"])) }]);
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await vi.waitFor(() => expect(screen.queryByRole("status")).toBeNull());
    expect(screen.queryByRole("heading")).toBeNull();
  });
});
