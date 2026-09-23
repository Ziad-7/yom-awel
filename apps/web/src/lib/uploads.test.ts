import { describe, it, expect, vi, afterEach } from "vitest";
import { validateFile, MAX_BYTES } from "./uploads";
import { request, ApiError } from "./api/client";

afterEach(() => vi.unstubAllGlobals());
describe("upload boundary", () => {
  it("rejects empty, oversized and executable files", () => {
    expect(validateFile({ name: "x.csv", size: 0 })).not.toBeNull();
    expect(validateFile({ name: "x.csv", size: MAX_BYTES + 1 })).not.toBeNull();
    expect(validateFile({ name: "x.csv.exe", size: 100 })).not.toBeNull();
    expect(validateFile({ name: "x.XLSX", size: MAX_BYTES })).toBeNull();
  });
  it("sends bearer and idempotency only in headers", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) });
    vi.stubGlobal("fetch", fetcher);
    await request("/api/v1/submissions", "private-token", {
      method: "POST",
      headers: { "Idempotency-Key": "retry-key" },
      body: "{}",
    });
    expect(fetcher.mock.calls[0][0]).not.toContain("private-token");
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer private-token",
    );
    expect(fetcher.mock.calls[0][1].headers["Idempotency-Key"]).toBe(
      "retry-key",
    );
  });
  it("maps authenticated-session failures into typed safe errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          status: 401,
          json: async () => ({ code: "unauthorized", message: "الجلسة انتهت" }),
        }),
    );
    await expect(request("/api/v1/skills", "expired")).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
