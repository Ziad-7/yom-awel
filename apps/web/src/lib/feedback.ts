import type { Lang } from "./i18n/keys";

export const FEEDBACK_SECTIONS = ["decision", "impact", "next", "score"] as const;
export type FeedbackSection = (typeof FEEDBACK_SECTIONS)[number];

/** The section headings the API validates every feedback text against (feedback/fallback.py). */
const HEADINGS: Record<Lang, readonly [string, string, string, string]> = {
  ar: ["القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:"],
  en: ["Decision:", "Business impact:", "Next action:", "Score explanation:"],
};

export type ParsedFeedback = {
  byline: string;
  sections: { id: FeedbackSection; body: string }[];
};

/** Splits Tarek's text into its four sections; null when it doesn't follow the contract. */
export function parseFeedback(text: string, lang: Lang): ParsedFeedback | null {
  const headings = HEADINGS[lang];
  const positions = headings.map((heading) => text.indexOf(heading));
  const ordered = positions.every((position, index) => position >= 0 && (index === 0 || position > positions[index - 1]));
  if (!ordered || headings.some((heading) => text.split(heading).length !== 2)) return null;
  const sections = FEEDBACK_SECTIONS.map((id, index) => ({
    id,
    body: text.slice(positions[index] + headings[index].length, positions[index + 1]).trim(),
  }));
  if (sections.some((section) => !section.body)) return null;
  return { byline: text.slice(0, positions[0]).trim(), sections };
}
