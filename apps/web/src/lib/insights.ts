import type { CellIssue, EmailInsight, ImpactMetric, TablePreview } from "./api/contract";
import type { Lang } from "./i18n/keys";

/** Latin digits in Arabic too, matching every other number in the interface. */
const LOCALE: Record<Lang, string> = { ar: "ar-EG-u-nu-latn", en: "en-EG" };

export function formatMetric(metric: ImpactMetric, lang: Lang): string {
  const value = Number(metric.value);
  const options: Intl.NumberFormatOptions =
    metric.unit === "egp"
      ? { style: "currency", currency: "EGP", minimumFractionDigits: Number.isInteger(value) ? 0 : 2, maximumFractionDigits: 2 }
      : { maximumFractionDigits: 0 };
  return new Intl.NumberFormat(LOCALE[lang], options).format(value);
}

export const isZero = (metric: ImpactMetric) => Number(metric.value) === 0;

export type Segment = { text: string; elements: string[] };

/**
 * Splits the learner's email at every highlighted span. The API counts offsets in code
 * points (Python str), so the text is indexed the same way here, never in UTF-16 units.
 */
export function emailSegments(email: EmailInsight): Segment[] {
  const chars = Array.from(email.text);
  const spans = email.elements.flatMap((element) =>
    element.found && element.start != null && element.end != null && element.start < element.end && element.end <= chars.length
      ? [{ id: element.element_id, start: element.start, end: element.end }]
      : [],
  );
  const cuts = [...new Set([0, chars.length, ...spans.flatMap((span) => [span.start, span.end])])].sort((a, b) => a - b);
  return cuts.slice(0, -1).flatMap((from, index) => {
    const to = cuts[index + 1];
    const text = chars.slice(from, to).join("");
    return text ? [{ text, elements: spans.filter((span) => span.start <= from && span.end >= to).map((span) => span.id) }] : [];
  });
}

export type XrayRow = { row: number; cells: string[]; issues: CellIssue[] };

export type TableXray = {
  rows: XrayRow[];
  /** Spreadsheet rows of the other copies of a duplicated value, keyed by `row:column`. */
  peers: Map<string, number[]>;
  /** Issues in rows past the preview window. */
  hidden: number;
  /** Column indexes with the flagged columns first, so highlights are visible without scrolling. */
  order: number[];
};

const cellKey = (row: number, column: string) => `${row}:${column}`;

export function tableXray(table: TablePreview, issues: CellIssue[], checkId: string | null, onlyIssues: boolean): TableXray {
  const selected = checkId ? issues.filter((issue) => issue.check_id === checkId) : issues;
  const byRow = new Map<number, CellIssue[]>();
  for (const issue of selected) byRow.set(issue.row, [...(byRow.get(issue.row) ?? []), issue]);
  const previewRows = new Set(table.rows.map((row) => row.row));
  const rows = table.rows
    .map((row) => ({ row: row.row, cells: row.cells, issues: byRow.get(row.row) ?? [] }))
    .filter((row) => !onlyIssues || row.issues.length > 0);
  const flagged = new Set(selected.map((issue) => issue.column));
  const order = table.columns
    .map((column, index) => ({ index, flagged: flagged.has(column) }))
    .sort((a, b) => Number(b.flagged) - Number(a.flagged))
    .map((column) => column.index);
  return {
    rows,
    peers: duplicatePeers(table, selected),
    hidden: selected.filter((issue) => !previewRows.has(issue.row)).length,
    order,
  };
}

function duplicatePeers(table: TablePreview, issues: CellIssue[]): Map<string, number[]> {
  const peers = new Map<string, number[]>();
  const columns = new Set(issues.filter((issue) => issue.issue === "duplicate_order_id").map((issue) => issue.column));
  for (const column of columns) {
    const index = table.columns.indexOf(column);
    if (index < 0) continue;
    const byValue = new Map<string, number[]>();
    for (const row of table.rows) {
      const value = (row.cells[index] ?? "").trim();
      if (value) byValue.set(value, [...(byValue.get(value) ?? []), row.row]);
    }
    for (const rows of byValue.values())
      if (rows.length > 1) for (const row of rows) peers.set(cellKey(row, column), rows.filter((other) => other !== row));
  }
  return peers;
}

export const peersOf = (xray: TableXray, issue: CellIssue) => xray.peers.get(cellKey(issue.row, issue.column)) ?? [];
