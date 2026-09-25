import { describe, expect, it } from "vitest";
import { ar } from "./ar";
import { en } from "./en";

function shape(value: unknown): unknown {
  if (typeof value === "function") return "function";
  if (Array.isArray(value)) return value.map(shape);
  if (value && typeof value === "object")
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, shape(item)]));
  return typeof value;
}
function strings(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (value && typeof value === "object") return Object.values(value).flatMap(strings);
  return [];
}

describe("bilingual dictionaries", () => {
  it("have the same shape in Arabic and English", () => {
    expect(shape(ar)).toEqual(shape(en));
  });
  it("have no empty strings and differ per language", () => {
    expect(strings(ar).every((text) => text.trim())).toBe(true);
    expect(strings(en).every((text) => text.trim())).toBe(true);
    expect(ar.persona.name).toBe("م. طارق");
    expect(en.persona.name).toBe("Eng. Tarek");
    expect(ar.persona.role).toBe("مشرف الفريق");
    expect(en.persona.role).toBe("Team Lead");
  });
});
