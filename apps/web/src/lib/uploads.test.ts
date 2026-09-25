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
  it("calls same-origin with the cookie and the CSRF header on writes", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) });
    vi.stubGlobal("fetch", fetcher);
    await request("/api/v1/submissions", {
      method: "POST",
      headers: { "Idempotency-Key": "retry-key" },
      body: "{}",
    });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("/api/v1/submissions");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-Yom-Awel"]).toBe("1");
    expect(init.headers.Authorization).toBeUndefined();
    expect(init.headers["Idempotency-Key"]).toBe("retry-key");
  });
  it("sends no CSRF header on reads", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) });
    vi.stubGlobal("fetch", fetcher);
    await request("/api/v1/skills");
    expect(fetcher.mock.calls[0][1].headers["X-Yom-Awel"]).toBeUndefined();
  });
  it("maps authenticated-session failures into typed safe errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ code: "unauthorized", message: "الجلسة انتهت" }),
      }),
    );
    await expect(request("/api/v1/skills")).rejects.toBeInstanceOf(ApiError);
  });
});
