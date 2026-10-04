import { describe, expect, it } from "vitest";
import type { EmailInsight, ImpactMetric } from "./api/contract";
import { emailSegments, formatMetric, isZero, peersOf, tableXray } from "./insights";
import { evaluation, insightsFor } from "../test/mock-api";

const metric = (value: string, unit: ImpactMetric["unit"]): ImpactMetric => ({ metric_id: "revenue_overstated", value, unit });

describe("formatMetric", () => {
  it("formats money as EGP with Latin digits in both languages", () => {
    expect(formatMetric(metric("1234.50", "egp"), "en")).toMatch(/EGP\s?1,234\.50$/);
    expect(formatMetric(metric("200.00", "egp"), "en")).toMatch(/EGP\s?200$/);
    const arabic = formatMetric(metric("1234.50", "egp"), "ar");
    expect(arabic).toMatch(/1,234\.50/);
    expect(arabic).not.toMatch(/[٠-٩]/);
  });

  it("formats counts as whole numbers and spots zero", () => {
    expect(formatMetric(metric("12", "customers"), "en")).toBe("12");
    expect(formatMetric(metric("1200", "orders"), "ar")).toBe("1,200");
    expect(isZero(metric("0.00", "egp"))).toBe(true);
    expect(isZero(metric("0.01", "egp"))).toBe(false);
  });
});

describe("emailSegments", () => {
  const email = (text: string, elements: EmailInsight["elements"]): EmailInsight => ({
    text,
    elements,
    word_count: 3,
    min_words: 1,
    max_words: 10,
  });

  it("splits overlapping spans and keeps the full text", () => {
    const text = "Order YA-2048 is late";
    const segments = emailSegments(
      email(text, [
        { element_id: "subject_order", check_id: "recipient_and_subject", found: true, start: 6, end: 13 },
        { element_id: "order_id", check_id: "case_facts", found: true, start: 0, end: 13 },
        { element_id: "refund", check_id: "action_plan", found: false, start: null, end: null },
      ]),
    );
    expect(segments.map((segment) => segment.text).join("")).toBe(text);
    expect(segments).toEqual([
      { text: "Order ", elements: ["order_id"] },
      { text: "YA-2048", elements: ["subject_order", "order_id"] },
      { text: " is late", elements: [] },
    ]);
  });

  it("counts offsets in code points like the API, not UTF-16 units", () => {
    const text = "🙂 Hi Salma";
    const [, highlighted] = emailSegments(
      email(text, [{ element_id: "greeting", check_id: "professional_closing", found: true, start: 5, end: 10 }]),
    );
    expect(highlighted).toEqual({ text: "Salma", elements: ["greeting"] });
  });

  it("ignores spans outside the text", () => {
    const segments = emailSegments(
      email("short", [{ element_id: "greeting", check_id: "professional_closing", found: true, start: 2, end: 99 }]),
    );
    expect(segments).toEqual([{ text: "short", elements: [] }]);
  });
});

describe("tableXray", () => {
  const insights = insightsFor(evaluation(["unique_orders", "standard_dates"]));
  const table = insights.table!;

  it("keeps only rows with issues and links duplicate copies to each other", () => {
    const xray = tableXray(table, insights.issues, null, true);
    expect(xray.rows.map((row) => row.row)).toEqual([2, 4, 5]);
    const [first] = xray.rows[0].issues;
    expect(peersOf(xray, first)).toEqual([4]);
    expect(xray.hidden).toBe(0);
  });

  it("filters by check and can show every row", () => {
    const dates = tableXray(table, insights.issues, "standard_dates", true);
    expect(dates.rows.map((row) => row.row)).toEqual([5]);
    expect(dates.order.map((index) => table.columns[index]).slice(0, 2)).toEqual(["order_date", "order_id"]);
    const all = tableXray(table, insights.issues, "standard_dates", false);
    expect(all.rows).toHaveLength(table.rows.length);
  });

  it("counts issues past the preview window", () => {
    const extra = [...insights.issues, { row: 500, column: "order_date", check_id: "standard_dates", issue: "nonstandard_date" }];
    expect(tableXray(table, extra, null, true).hidden).toBe(1);
  });
});
