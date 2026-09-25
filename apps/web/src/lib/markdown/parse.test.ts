import { describe, expect, it } from "vitest";
import { parseInline, parseMarkdown } from "./parse";

describe("safe markdown subset", () => {
  it("parses headings, rules, nested lists, bold and code", () => {
    const blocks = parseMarkdown("# Title\n\n1. **Bold `code`:**\n   - child\n2. second\n\n---\ntext\nmore");
    expect(blocks.map((block) => block.kind)).toEqual(["heading", "list", "rule", "paragraph"]);
    const list = blocks[1];
    if (list.kind !== "list") throw new Error("expected list");
    expect(list.ordered).toBe(true);
    expect(list.items).toHaveLength(2);
    expect(list.items[0].children).toHaveLength(1);
    expect(list.items[0].inlines[0]).toEqual({
      kind: "strong",
      children: [
        { kind: "text", text: "Bold " },
        { kind: "code", text: "code" },
        { kind: "text", text: ":" },
      ],
    });
  });

  it("keeps raw HTML and unpaired markers as plain text", () => {
    expect(parseInline("<img src=x onerror=alert(1)>")).toEqual([
      { kind: "text", text: "<img src=x onerror=alert(1)>" },
    ]);
    expect(parseInline("2 ** 3")).toEqual([{ kind: "text", text: "2 ** 3" }]);
  });
});
