import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Certificate } from "../lib/api/contract";
import { LanguageProvider } from "../lib/i18n/language";
import type { Lang } from "../lib/i18n/keys";
import { CertificateCard, CertificateVerification } from "./certificate";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const TOKEN = "A".repeat(43);
const CERTIFICATE: Certificate = {
  token: TOKEN,
  display_name: "Sara",
  tasks: [
    {
      task_id: "clean-sales",
      title_ar: "تنظيف بيانات المبيعات",
      title_en: "Clean the sales data",
      score: 100,
      attempts: 2,
      passed_at: "2026-10-05T10:00:00Z",
      checks: ["unique_orders", "standard_dates"],
    },
  ],
  skills: [{ skill_id: "data_cleaning", evidence: ["unique_orders", "standard_dates"] }],
  verified_at: "2026-10-05T12:00:00Z",
};

function respond(status: number, body: unknown = { code: status === 404 ? "not_found" : "x" }) {
  const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

function mount(node: React.ReactNode, lang: Lang = "en") {
  render(<LanguageProvider initialLang={lang}>{node}</LanguageProvider>);
}

describe("CertificateVerification", () => {
  it("shows a verified certificate with its tasks and the checks that prove each skill", async () => {
    const fetch = respond(200, CERTIFICATE);
    mount(<CertificateVerification token={TOKEN} />);

    expect(await screen.findByRole("heading", { level: 1, name: "Verified skills certificate" })).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(`/api/v1/certificates/${TOKEN}`, expect.anything());
    expect(screen.getByText("Sara")).toBeInTheDocument();
    expect(screen.getByText("Clean the sales data")).toBeInTheDocument();
    expect(screen.getByText(/after 2 attempts/)).toBeInTheDocument();
    expect(screen.getByText("Data cleaning")).toBeInTheDocument();
    expect(screen.getByText("Proven by: Unique orders, Standard dates")).toBeInTheDocument();
  });

  it("says plainly when a link does not verify, in the language the link carries", async () => {
    respond(404);
    mount(<CertificateVerification token={TOKEN} lang="ar" />, "en");
    expect(await screen.findByRole("heading", { level: 1, name: "مش قادرين نتحقق من الشهادة دي" })).toBeInTheDocument();
  });

  it("does not call a certificate invalid when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("offline"))));
    mount(<CertificateVerification token={TOKEN} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/network connection/);
    expect(screen.queryByText("This certificate can't be verified")).toBeNull();
  });
});

describe("CertificateCard", () => {
  it("invites a learner without a pass to earn one", async () => {
    respond(404);
    mount(<CertificateCard />);
    expect(await screen.findByText("Pass any task to earn your verified skills certificate.")).toBeInTheDocument();
  });

  it("shares a verify link with a QR code and copies it", async () => {
    respond(200, CERTIFICATE);
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    mount(<CertificateCard />);

    const link = await screen.findByLabelText("Certificate link");
    expect(link).toHaveValue(`${window.location.origin}/verify/${TOKEN}?lang=en`);
    expect(screen.getByRole("img", { name: "QR code for Sara's certificate" }).querySelector("path")?.getAttribute("d")).toMatch(/^M\d/);
    fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/verify/${TOKEN}?lang=en`));
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
  });
});
