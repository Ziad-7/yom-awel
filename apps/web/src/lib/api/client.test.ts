import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiHeaders, request } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("same-origin API client", () => {
  it("adds the CSRF guard to state-changing requests only", () => {
    expect(apiHeaders({ method: "POST" })).toMatchObject({ "X-Yom-Awel": "1" });
    expect(apiHeaders({ method: "put", body: "{}" })).toMatchObject({
      "X-Yom-Awel": "1",
      "Content-Type": "application/json",
    });
    expect(apiHeaders({})).not.toHaveProperty("X-Yom-Awel");
  });

  it("calls relative /api/v1 paths with same-origin credentials and no bearer token", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    await request("/submissions", {
      method: "POST",
      headers: { "Idempotency-Key": "retry-key" },
      body: "{}",
    });
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("/api/v1/submissions");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers).not.toHaveProperty("Authorization");
    expect(init.headers["Idempotency-Key"]).toBe("retry-key");
  });

  it("maps failures to typed codes without exposing server text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: "unauthorized", message: "x" }), { status: 401 })),
    );
    await expect(request("/skills")).rejects.toMatchObject({ status: 401, code: "unauthorized" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
    await expect(request("/skills")).rejects.toMatchObject({ status: 0, code: "offline" });
  });

  it("refuses protocol-relative paths", async () => {
    await expect(request("//evil.example/x")).rejects.toBeInstanceOf(ApiError);
  });
});
