import { useMemo } from "react";
import { parseMarkdown, type Block, type Inline, type ListItem } from "../lib/markdown/parse";

function Inlines({ inlines }: { inlines: Inline[] }) {
  return inlines.map((inline, index) => {
    if (inline.kind === "code") return <code key={index}>{inline.text}</code>;
    if (inline.kind === "strong")
      return (
        <strong key={index}>
          <Inlines inlines={inline.children} />
        </strong>
      );
    return inline.text;
  });
}

function Items({ items, ordered }: { items: ListItem[]; ordered: boolean }) {
  const content = items.map((item, index) => (
    <li key={index}>
      <Inlines inlines={item.inlines} />
      {item.children.length > 0 && <Items items={item.children} ordered={false} />}
    </li>
  ));
  return ordered ? <ol>{content}</ol> : <ul>{content}</ul>;
}

function Heading({ level, children }: { level: number; children: React.ReactNode }) {
  const Tag = `h${Math.min(level, 6)}` as "h3";
  return <Tag>{children}</Tag>;
}

function BlockView({ block, headingBase }: { block: Block; headingBase: number }) {
  switch (block.kind) {
    case "heading":
      return (
        <Heading level={headingBase + block.level - 1}>
          <Inlines inlines={block.inlines} />
        </Heading>
      );
    case "rule":
      return <hr />;
    case "list":
      return <Items items={block.items} ordered={block.ordered} />;
    case "paragraph":
      return (
        <p>
          <Inlines inlines={block.inlines} />
        </p>
      );
  }
}

/** Renders trusted-shape, untrusted-content markdown as React text nodes only. */
export function Markdown({ source, headingBase = 3 }: { source: string; headingBase?: number }) {
  const blocks = useMemo(() => parseMarkdown(source), [source]);
  return (
    <div className="markdown">
      {blocks.map((block, index) => (
        <BlockView key={index} block={block} headingBase={headingBase} />
      ))}
    </div>
  );
}
