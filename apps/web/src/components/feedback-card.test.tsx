import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LanguageProvider } from "../lib/i18n/language";
import { feedback } from "../test/mock-api";
import { FeedbackCard } from "./feedback-card";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function mount(passed = false) {
  render(
    <LanguageProvider initialLang="en">
      <FeedbackCard submissionId="00000000-0000-4000-8000-00000000000b" initial={feedback("en")} passed={passed} />
    </LanguageProvider>,
  );
}

describe("FeedbackCard", () => {
  it("shows Tarek's four sections with the decision coloured by the verdict", () => {
    mount(false);
    const headings = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headings).toEqual(["Decision", "Business impact", "Next action", "Score explanation"]);
    expect(screen.getByText("submission needs rework.").closest("section")).toHaveClass("is-decision", "rework");
    expect(screen.getAllByText("Eng. Tarek, Team Lead")).toHaveLength(1);
  });

  it("hides read-aloud where the browser has no speech engine", () => {
    mount();
    expect(screen.queryByRole("button", { name: /Listen/ })).toBeNull();
  });

  it("reads the feedback aloud in its language, and stops on demand", () => {
    const speak = vi.fn();
    const cancel = vi.fn();
    vi.stubGlobal("speechSynthesis", { speak, cancel, getVoices: () => [{ lang: "en-GB", name: "English" }] });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        lang = "";
        voice: unknown = null;
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;
        constructor(public text: string) {}
      },
    );
    mount();

    fireEvent.click(screen.getByRole("button", { name: /Listen/ }));
    const utterance = speak.mock.calls[0][0];
    expect(utterance.lang).toBe("en-US");
    expect(utterance.voice).toEqual({ lang: "en-GB", name: "English" });
    expect(utterance.text).toContain("Business impact. duplicate orders inflate revenue.");
    expect(screen.getByRole("button", { name: /Stop/ })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: /Stop/ }));
    expect(cancel).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Listen/ })).toHaveAttribute("aria-pressed", "false");
  });
});
