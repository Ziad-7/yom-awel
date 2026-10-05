import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CoachAnswer } from "../lib/api/contract";
import { LanguageProvider } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import { AskTarek } from "./ask-tarek";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const SUBMISSION = "00000000-0000-4000-8000-00000000000b";
const ANSWER: CoachAnswer = {
  answer: "Unique orders failed: rows 10 and 19 repeat an order ID.",
  language: "en",
  source: "gemini",
  grounded_on: ["Spreadsheet row 10, column order_id: duplicate order ID."],
};

function mount(responses: Array<[number, unknown]>, lang: Lang = "en") {
  const fetch = vi.fn(async () => {
    const [status, body] = responses.length > 1 ? responses.shift()! : responses[0];
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetch);
  render(
    <LanguageProvider initialLang={lang}>
      <AskTarek submissionId={SUBMISSION} />
    </LanguageProvider>,
  );
  return fetch;
}

describe("AskTarek", () => {
  it("asks a suggested question in the interface language and shows a grounded answer", async () => {
    const fetch = mount([[200, ANSWER]]);
    fireEvent.click(screen.getByRole("button", { name: "Where exactly are my mistakes?" }));

    expect(await screen.findByText(ANSWER.answer)).toBeInTheDocument();
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`/api/v1/submissions/${SUBMISSION}/questions`);
    expect(JSON.parse(init.body as string)).toEqual({ question: "Where exactly are my mistakes?", language: "en" });
    expect(new Headers(init.headers).get("x-yom-awel")).toBe("1");
    const thread = screen.getByRole("list", { name: "Ask Tarek" });
    expect(within(thread).getByText("AI answer, checked against your results")).toBeInTheDocument();
    expect(within(thread).getByText(ANSWER.grounded_on[0])).toBeInTheDocument();
  });

  it("asks a typed question in Arabic and labels a guide answer", async () => {
    const fetch = mount([[200, { ...ANSWER, language: "ar-EG", source: "guide", answer: "اللي الفحوصات لقته:" }]], "ar");
    fireEvent.change(screen.getByLabelText("سؤالك"), { target: { value: "أصلّح إيه الأول؟" } });
    fireEvent.click(screen.getByRole("button", { name: "اسأل" }));

    const answer = await screen.findByText("اللي الفحوصات لقته:");
    expect(answer.closest(".ask-answer")).toHaveAttribute("dir", "rtl");
    expect(screen.getByText("رد مبني على فحوصاتك")).toBeInTheDocument();
    expect(JSON.parse((fetch.mock.calls[0] as unknown as [string, RequestInit])[1].body as string).language).toBe("ar-EG");
    await waitFor(() => expect(screen.getByLabelText("سؤالك")).toHaveValue(""));
  });

  it("explains the question budget instead of a generic error", async () => {
    mount([[429, { code: "rate_limited" }]]);
    fireEvent.click(screen.getByRole("button", { name: "Why didn't I pass?" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tarek needs a minute");
  });
});
