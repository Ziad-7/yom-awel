/**
 * A deliberately small markdown subset for task content: headings, rules, paragraphs,
 * one level of nested lists, bold and inline code. It produces data, never HTML, so raw
 * HTML in the source is shown as text and cannot execute.
 */
export type Inline =
  | { kind: "text"; text: string }
  | { kind: "code"; text: string }
  | { kind: "strong"; children: Inline[] };
export type ListItem = { inlines: Inline[]; children: ListItem[] };
export type Block =
  | { kind: "heading"; level: number; inlines: Inline[] }
  | { kind: "rule" }
  | { kind: "paragraph"; inlines: Inline[] }
  | { kind: "list"; ordered: boolean; items: ListItem[] };

const HEADING = /^(#{1,6})\s+(.*)$/;
const RULE = /^\s*(-{3,}|\*{3,})\s*$/;
const ITEM = /^(\s*)([-*]|\d+\.)\s+(.*)$/;

/** Splits on a paired delimiter; unpaired delimiters stay literal text. */
function paired(text: string, delimiter: string): { inside: boolean; text: string }[] {
  const parts = text.split(delimiter);
  if (parts.length % 2 === 0) return [{ inside: false, text }];
  return parts
    .map((part, index) => ({ inside: index % 2 === 1, text: part }))
    .filter((part) => part.text !== "");
}

function codeSpans(text: string): Inline[] {
  return paired(text, "`").map((part) =>
    part.inside ? { kind: "code", text: part.text } : { kind: "text", text: part.text },
  );
}

export function parseInline(text: string): Inline[] {
  return paired(text, "**").flatMap((part): Inline[] =>
    part.inside ? [{ kind: "strong", children: codeSpans(part.text) }] : codeSpans(part.text),
  );
}

export function parseMarkdown(source: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: Extract<Block, { kind: "list" }> | null = null;

  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", inlines: parseInline(paragraph.join(" ")) });
    paragraph = [];
    list = null;
  };

  for (const raw of source.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    const heading = HEADING.exec(line);
    const item = ITEM.exec(line);
    if (!line.trim()) flush();
    else if (heading) {
      flush();
      blocks.push({ kind: "heading", level: heading[1].length, inlines: parseInline(heading[2]) });
    } else if (RULE.test(line)) {
      flush();
      blocks.push({ kind: "rule" });
    } else if (item) {
      const entry: ListItem = { inlines: parseInline(item[3]), children: [] };
      const parent = list?.items.at(-1);
      if (item[1].length > 0 && parent) parent.children.push(entry);
      else if (list) list.items.push(entry);
      else {
        flush();
        list = { kind: "list", ordered: /\d/.test(item[2]), items: [entry] };
        blocks.push(list);
      }
    } else if (list) list.items.at(-1)?.inlines.push({ kind: "text", text: " " }, ...parseInline(line.trim()));
    else paragraph.push(line.trim());
  }
  flush();
  return blocks;
}
