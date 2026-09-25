export const LANGS = ["ar", "en"] as const;
export type Lang = (typeof LANGS)[number];
export type ApiLanguage = "ar-EG" | "en";

export type TaskStatus = "available" | "in_progress" | "completed";
export type CheckId =
  | "unique_orders"
  | "standard_dates"
  | "valid_numeric_values"
  | "complete_customer_records"
  | "report_columns"
  | "paid_regions"
  | "paid_order_counts"
  | "paid_revenue"
  | "recipient_and_subject"
  | "case_facts"
  | "action_plan"
  | "professional_closing";
export type SkillId =
  | "data_cleaning"
  | "attention_to_detail"
  | "sql_reporting"
  | "customer_communication";
export const REJECTION_CODES = [
  "unsupported_type",
  "artifact_too_large",
  "mime_mismatch",
  "expanded_size_exceeded",
  "sheet_limit_exceeded",
  "artifact_unreadable",
  "missing_columns",
  "duplicate_columns",
  "too_few_rows",
  "empty_file",
] as const;
export type RejectionCode = (typeof REJECTION_CODES)[number];

export const toApiLanguage = (lang: Lang): ApiLanguage =>
  lang === "ar" ? "ar-EG" : "en";
export const fromApiLanguage = (language: ApiLanguage): Lang =>
  language === "ar-EG" ? "ar" : "en";
export const directionOf = (lang: Lang) => (lang === "ar" ? "rtl" : "ltr");
export const isLang = (value: unknown): value is Lang =>
  LANGS.includes(value as Lang);
export const isRejectionCode = (value: string): value is RejectionCode =>
  REJECTION_CODES.includes(value as RejectionCode);
export const isCheckId = (value: string): value is CheckId =>
  Object.hasOwn(CHECK_IDS, value);
export const isSkillId = (value: string): value is SkillId =>
  Object.hasOwn(SKILL_IDS, value);

const CHECK_IDS: Record<CheckId, true> = {
  unique_orders: true,
  standard_dates: true,
  valid_numeric_values: true,
  complete_customer_records: true,
  report_columns: true,
  paid_regions: true,
  paid_order_counts: true,
  paid_revenue: true,
  recipient_and_subject: true,
  case_facts: true,
  action_plan: true,
  professional_closing: true,
};
const SKILL_IDS: Record<SkillId, true> = {
  data_cleaning: true,
  attention_to_detail: true,
  sql_reporting: true,
  customer_communication: true,
};
