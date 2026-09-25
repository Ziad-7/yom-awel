import { describe, expect, it } from "vitest";
import { ApiError } from "./api/client";
import { en } from "./i18n/en";
import { REJECTION_CODES } from "./i18n/keys";
import { errorMessage, rejectionMessage } from "./messages";

describe("error copy", () => {
  it("covers every rejection code with its own message", () => {
    const messages = REJECTION_CODES.map((code) => rejectionMessage(en, code));
    expect(new Set(messages).size).toBe(REJECTION_CODES.length);
    expect(messages).not.toContain(en.rejections.unknown);
  });
  it("never shows raw server text", () => {
    expect(errorMessage(en, new ApiError(503, "unavailable"))).toBe(en.errors.service);
    expect(errorMessage(en, new ApiError(413, "too_large"))).toBe(en.rejections.artifact_too_large);
    expect(errorMessage(en, new Error("Traceback: secret"))).toBe(en.errors.generic);
  });
});
