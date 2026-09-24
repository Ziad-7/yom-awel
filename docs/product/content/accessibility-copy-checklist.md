# Yom Awel Content & RTL Accessibility Specification

This specification freezes mandatory accessibility, layout, and comprehension requirements for all learner-facing interfaces (Web at `apps/web` and Telegram bot at `@yom_awel_bot`). Member 5 uses these rules as the contract for Playwright and Axe testing.

---

## 1. RTL Layout & Mixed-Language Rendering

- **Document Root:** Root container sets `dir="rtl"` and `lang="ar-EG"`.
- **Bidirectional Isolation (`<bdi>`):**
  - Mixed Arabic/English identifiers (e.g. `order_id`, `sales_cleaned.csv`, `YYYY-MM-DD`, `quantity * unit_price`, `score / 100`, attempt counts) must be wrapped in `<bdi>` or `<span dir="ltr">`.
  - Punctuation, dashes, parentheses, and colons must not invert or bleed across language boundaries.
- **Reading Order:** Logical reading order strictly matches DOM source order; float or flex order tricks that invert visual order from keyboard navigation order are forbidden.

---

## 2. Keyboard Navigation & Focus Management

- **Logical Tab Order:** All interactive elements (inputs, buttons, tabs, modal close triggers) are reachable in a natural sequential flow using `Tab` and `Shift+Tab`.
- **Keyboard Actuation:** Buttons activate on `Enter` and `Space`. Dialog backdrops and modal dialogs close on `Escape`.
- **Visible Focus Indicator:**
  - Every focused interactive element must display a visible focus indicator with at least 2px solid offset outline.
  - Focus ring must achieve a contrast ratio >= 3:1 against surrounding background elements.
- **Focus Shifts on Dynamic Transitions:**
  - Upon submission completion or failure transition to `NEEDS_RETRY`, focus shifts programmatically to the results summary heading (`<h2 id="result-heading" tabIndex={-1}>`) to orient screen reader and keyboard users.

---

## 3. Screen Reader & ARIA Semantics

- **Async Announcements (`aria-live`):**
  - Submission processing state (`state.loading`) uses `aria-live="polite"` to notify the learner when evaluation completes without requiring manual polling.
  - Critical or blocking alerts (e.g. `network.offline`, `upload.invalid_type`) use `aria-live="assertive"`.
- **Error-to-Control Association:**
  - Rejection messages link directly to the target control using `aria-describedby="[error-message-id]"`.
  - Invalid inputs must programmatically set `aria-invalid="true"`.
- **Accessible Labels:**
  - All status banners, badges, and icon buttons must supply descriptive `aria-label` or `aria-labelledby` referencing stable strings from `interface-copy.yaml`.

---

## 4. Visual Contrast & Multi-Modal Status (No Color-Only State)

- **Color Independence:**
  - Success, retry, warning, and error states must **never** be conveyed by color alone.
  - Every status badge or card must pair color with:
    1. A clear textual label (e.g., `"✓ نجح"`, `"! يحتاج مراجعة"`, `"✕ غير مدعوم"`).
    2. An explicit semantic icon (`✓`, `!`, `✕`).
- **Contrast Ratios (WCAG 2.1 AA):**
  - Normal text: >= 4.5:1 against background.
  - Large text (>= 18pt or >= 14pt bold): >= 3:1.
  - Essential graphical UI elements (icons, borders): >= 3:1.

---

## 5. Mobile Viewport & Touch Ergonomics (375 px)

- **Small Viewport Guarantee:**
  - The interface must remain 100% functional, readable, and operable at a minimum screen width of **375 px** (standard iPhone SE / small mobile viewport).
  - **Zero Horizontal Overflow:** Page body and all cards must fit entirely within 375 px width without horizontal scrolling.
- **Touch Target Sizes:**
  - All buttons, file upload triggers, and interactive controls must have a minimum clickable/tappable area of **44 × 44 CSS pixels**.
  - Minimum 8px spacing between adjacent touch targets to prevent accidental taps.

---

## 6. Self-Explaining Experience & Actionable States

- First-time learners must understand the task brief, upload boundaries, evaluation feedback, and retry procedure entirely from the interface copy, without requiring developer assistance.
- Every error message must specify:
  1. What happened.
  2. The action label shown on the button.
  3. The expected state after clicking the action button.

