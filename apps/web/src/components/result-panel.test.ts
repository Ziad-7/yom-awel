import { describe, expect, it } from "vitest";
import { evaluation } from "../test/mock-api";
import { verdictOf } from "./result-panel";

const critical = new Set(["unique_orders"]);

describe("result verdict", () => {
  it("distinguishes pass, rejection, critical failure and plain failure", () => {
    expect(verdictOf(evaluation(), 75, critical)).toBe("passed");
    expect(verdictOf(evaluation([], ["missing_columns"]), 75, critical)).toBe("rejected");
    expect(verdictOf(evaluation(["unique_orders"]), 75, critical)).toBe("critical_failed");
    expect(verdictOf(evaluation(["standard_dates", "unique_orders"]), 75, critical)).toBe("failed");
  });
});
