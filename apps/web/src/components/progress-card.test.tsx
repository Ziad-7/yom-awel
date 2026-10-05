import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Attempt } from "../lib/api/contract";
import { LanguageProvider } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import { clearInsightsCache } from "../lib/progress";
import { evaluation, insightsFor } from "../test/mock-api";
import { ProgressCard } from "./progress-card";

afterEach(() => {
  cleanup();
  clearInsightsCache();
  vi.unstubAllGlobals();
});

const attempt = (attempt_number: number, failing: string[] = [], errors: string[] = []) =>
  ({ submission_id: `00000000-0000-4000-8000-00000000000${attempt_number}`, attempt_number, evaluation: evaluation(failing, errors) }) as Attempt;

function mount(history: Attempt[], current: Attempt, lang: Lang = "en") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const found = history.find((item) => String(input).includes(item.submission_id));
      return new Response(JSON.stringify(insightsFor(found!.evaluation)), { status: 200, headers: { "Content-Type": "application/json" } });
    }),
  );
  render(
    <LanguageProvider initialLang={lang}>
      <ProgressCard current={current} history={history} threshold={75} />
    </LanguageProvider>,
  );
}

describe("ProgressCard", () => {
  it("shows the score gain, what was fixed, the cost recovered and a score chart", async () => {
    const history = [attempt(1, ["unique_orders", "standard_dates"]), attempt(2, ["unique_orders"]), attempt(3)];
    mount(history, history[2]);

    const card = screen.getByRole("region", { name: "Progress since attempt 2" });
    expect(card).toHaveTextContent("+25 points");
    expect(card).toHaveTextContent("75 → 100");
    const fixed = within(card).getByText("Unique orders").closest("li")!;
    expect(fixed).toHaveClass("fixed");
    expect(await within(fixed).findByText("2 → 0 issues")).toBeInTheDocument();
    expect(await within(card).findByText("Revenue inflated by duplicate orders")).toBeInTheDocument();
    expect(within(card).getByText(/EGP\s?200 → EGP\s?0/)).toBeInTheDocument();

    const points = within(card).getAllByRole("img");
    expect(points.map((point) => point.getAttribute("aria-label"))).toEqual([
      "Attempt 1: 50, not passed",
      "Attempt 2: 75, not passed",
      "Attempt 3: 100, passed",
    ]);
    fireEvent.focus(points[1]);
    expect(card.querySelector(".chart-tooltip")).toHaveTextContent("Attempt 2: 75, not passed");
    expect(within(card).getByRole("table", { hidden: true })).toHaveTextContent("Not passed");
  });

  it("says when the last file was rejected, in Arabic", async () => {
    const history = [attempt(1, [], ["missing_columns"]), attempt(2, ["standard_dates"])];
    mount(history, history[1], "ar");
    expect(await screen.findByText(/المرة اللي فاتت الملف اترفض/)).toBeInTheDocument();
    expect(screen.getByText("+75 درجة")).toBeInTheDocument();
  });

  it("stays hidden on a first attempt and on a rejected one", () => {
    mount([attempt(1)], attempt(1));
    expect(screen.queryByRole("region")).toBeNull();
    cleanup();
    const history = [attempt(1), attempt(2, [], ["missing_columns"])];
    mount(history, history[1]);
    expect(screen.queryByRole("region")).toBeNull();
  });
});
