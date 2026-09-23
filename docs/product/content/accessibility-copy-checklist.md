# Yom Awel Content & RTL Accessibility Checklist

This checklist defines mandatory accessibility and comprehension requirements for all learner-facing interfaces (Web and Telegram).

---

## 1. RTL Reading Order & Layout
- [ ] **Document Direction:** Root HTML tag or container specifies `dir="rtl"` and `lang="ar-EG"`.
- [ ] **Natural Reading Hierarchy:** Page flows logically from right to left; primary action buttons, breadcrumbs, and status icons align to appropriate visual sides.
- [ ] **Bidirectional Text Isolation:** Numbers, file extensions (`.xlsx`, `.csv`), formula strings (`quantity * price`), and ISO formats (`YYYY-MM-DD`) use Unicode isolation (`<bdi>` or `dir="ltr"`) to prevent reversed punctuation or distorted hyphenation.

---

## 2. Keyboard Navigation & Focus Management
- [ ] **Full Tab Operability:** File drag-and-drop area, file browse button, and submission trigger are reachable and operable via keyboard alone (`Tab`, `Enter`, `Space`).
- [ ] **Focus on State Change:** When evaluation completes or transitions to `NEEDS_RETRY`, focus shifts gracefully to the results summary heading or status region.
- [ ] **Clear Focus Rings:** Interactive controls provide high-contrast visible focus indicators (`outline`) satisfying WCAG 2.4.7.

---

## 3. Screen Reader & ARIA Semantics
- [ ] **Independent Accessible Labels:** Controls with icons or abbreviated text supply full `aria-label` or `aria-describedby` references matching `interface-copy.yaml`.
- [ ] **Live Regions for Async Operations:** Processing states (`evaluation.loading`) use `aria-live="polite"` so screen reader users are notified when evaluation completes without requiring manual refresh.
- [ ] **Error-Control Association:** File rejection messages (`upload.invalid_type`, `upload.too_large`) link programmatically to the file input element using `aria-errormessage`.

---

## 4. Color & Contrast Non-Dependence
- [ ] **Multi-Modal Status Indicators:** Pass and fail states never rely on green or red color alone. Every result badge includes explicit text labels and semantic icons (e.g. checkmark vs. warning triangle).
- [ ] **Contrast Compliance:** Text and icon contrast ratios achieve at least 4.5:1 against card and page backgrounds (WCAG AA).

---

## 5. Independent Learner Comprehension
- [ ] **Self-Explaining Experience:** A first-time learner must understand the task brief, upload constraints, feedback notes, and retry procedure without verbal developer coaching.
- [ ] **Actionable Errors:** Error and retry notices inform the learner *what happened* and *what step to take next*.
