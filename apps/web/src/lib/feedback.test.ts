import { describe, expect, it } from "vitest";
import { parseFeedback } from "./feedback";

const EN = `Eng. Tarek, Team Lead
Decision: submission needs rework. Duplicate orders block passing, whatever the score.
Business impact: duplicate orders inflate total revenue.
Next action: keep exactly one row per order, then upload the file again.
Score explanation: 75 of 100; the pass mark is 75.`;

const AR = `م. طارق، مشرف الفريق
القرار: التسليم محتاج إعادة شغل.
تأثير الشغل: الطلبات المكررة بتنفخ الإيراد.
الخطوة الجاية: سيب صف واحد لكل طلب.
تفسير الدرجة: 75 من 100.`;

describe("parseFeedback", () => {
  it("splits English feedback into its byline and four sections", () => {
    const parsed = parseFeedback(EN, "en");
    expect(parsed?.byline).toBe("Eng. Tarek, Team Lead");
    expect(parsed?.sections.map((section) => section.id)).toEqual(["decision", "impact", "next", "score"]);
    expect(parsed?.sections[0].body).toBe("submission needs rework. Duplicate orders block passing, whatever the score.");
    expect(parsed?.sections[3].body).toBe("75 of 100; the pass mark is 75.");
  });

  it("splits Arabic feedback with Arabic headings", () => {
    const parsed = parseFeedback(AR, "ar");
    expect(parsed?.byline).toBe("م. طارق، مشرف الفريق");
    expect(parsed?.sections[2].body).toBe("سيب صف واحد لكل طلب.");
  });

  it("accepts feedback written on one line", () => {
    expect(parseFeedback(EN.replaceAll("\n", " "), "en")?.sections[1].body).toBe("duplicate orders inflate total revenue.");
  });

  it.each([
    ["a missing section", EN.replace("Business impact:", "Impact:")],
    ["sections out of order", EN.replace("Next action:", "TEMP").replace("Business impact:", "Next action:").replace("TEMP", "Business impact:")],
    ["a repeated heading", `${EN} Decision: again.`],
    ["an empty section", EN.replace("duplicate orders inflate total revenue.", "")],
    ["the other language's headings", EN],
  ])("returns null for %s", (_, text) => {
    expect(parseFeedback(text, text === EN ? "ar" : "en")).toBeNull();
  });
});
