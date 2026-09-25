import { ar } from "./ar";
import { en, type Dictionary } from "./en";
import type { Lang } from "./keys";

export const LANG_COOKIE = "yom_lang";
export const dictionaries: Record<Lang, Dictionary> = { ar, en };
