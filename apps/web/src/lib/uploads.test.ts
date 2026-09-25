import { describe, expect, it } from "vitest";
import { MAX_BYTES, uploadPath, validateFile, validateSignature } from "./uploads";

describe("upload boundary", () => {
  it("rejects empty, oversized and executable files", () => {
    expect(validateFile({ name: "x.csv", size: 0 })).toBe("empty_file");
    expect(validateFile({ name: "x.csv", size: MAX_BYTES + 1 })).toBe("artifact_too_large");
    expect(validateFile({ name: "x.csv.exe", size: 100 })).toBe("unsupported_type");
    expect(validateFile({ name: "x.XLSX", size: MAX_BYTES })).toBeNull();
  });

  it("requires a zip signature for .xlsx files", () => {
    expect(validateSignature("a.xlsx", new Uint8Array([0x50, 0x4b, 0x03, 0x04]))).toBeNull();
    expect(validateSignature("a.xlsx", new TextEncoder().encode("id,x"))).toBe("mime_mismatch");
    expect(validateSignature("a.csv", new Uint8Array([0]))).toBeNull();
  });

  it("only accepts upload URLs under the same-origin API proxy", () => {
    expect(uploadPath("/api/v1/artifacts/abc/content")).toBe("/artifacts/abc/content");
    for (const url of ["https://evil.example/x", "//evil.example/api/v1/x", "/api/v1/../admin", null])
      expect(() => uploadPath(url)).toThrow();
  });
});
