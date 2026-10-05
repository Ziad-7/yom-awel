import type {
  CheckId,
  EmailElementId,
  IssueCode,
  MetricId,
  RegionStatus,
  RejectionCode,
  SampleId,
  SkillId,
  TaskStatus,
  TourStep,
} from "./keys";
import type { FeedbackSection } from "../feedback";

type CheckCopy = { title: string; description: string };
type MetricCopy = { label: string; hint: string };
type SampleCopy = { title: string; note: string };
type StepCopy = { title: string; hint: string };
type MissionTask = "clean-sales" | "sql-report" | "client-email";

export const en = {
  meta: {
    title: "Yom Awel | Your work starts here",
    description:
      "Real work experience, step by step. Practise digital skills through hands-on tasks.",
  },
  shell: {
    brand: "Yom Awel",
    tagline: "Your experience starts here",
    home: "Yom Awel, home",
    skip: "Skip to content",
    navLabel: "Main navigation",
    nav: { tasks: "Tasks", work: "My desk", skills: "Skills & progress" },
    area: "Learning space",
    workspace: "Workspace",
    sideTitle: "Every attempt counts.",
    sideBody: "Mistakes are part of learning here. Try, get feedback, come back stronger.",
    guest: "Your seat is waiting",
    guestHint: "Start your first workday",
    role: "Trainee · Data team",
    modeLocal: "Local demo",
    modeCloud: "Live",
    providerGemini: "AI coaching on",
    providerDeterministic: "Offline coaching",
    footer: "Yom Awel · a safe place to learn by doing.",
    day: "Day",
  },
  language: {
    switchTo: "العربية",
    switchLabel: "التحويل إلى العربية",
    switchLang: "ar",
  },
  status: {
    booting: "Opening your workspace…",
    joining: "Setting up your desk…",
    starting: "Opening the task…",
    uploading: "Uploading your file securely…",
    evaluating: "Evaluating spreadsheet and auditing data quality, please wait a few seconds...",
    checking: "Checking your submission result…",
    savingLanguage: "Saving your language…",
  },
  errors: {
    generic: "Something went wrong. Please try again.",
    offline:
      "There seems to be a network connection problem. Please check your connection and try again.",
    session: "Your session has ended. Start a new session.",
    service:
      "A temporary processing error occurred while evaluating your submission. Your data is safe; please retry.",
    notStartable: "This task can't be started right now.",
    stillProcessing:
      "Your submission is still being reviewed. Use “Check result” in a moment.",
    dismiss: "Dismiss alert",
    retry: "Retry connection",
    alert: "Alert",
  },
  onboarding: {
    tag: "Welcome to the team",
    heading: "You don't need experience to start building experience.",
    body: "Your first assignment is waiting: a sales file that needs cleaning, and a team lead who helps you see the impact of your work.",
    steps: ["Receive the task", "Try it hands-on", "Learn from the result"],
    formTitle: "Shall we get acquainted?",
    formHint: "Write the name you'd like us to call you.",
    nameLabel: "Your name",
    namePlaceholder: "e.g. Ahmed",
    languageLegend: "Interface and feedback language",
    arabic: "العربية (مصر)",
    english: "English",
    submit: "Start my first workday",
    privacy:
      "No email or password. Clearing browser data or starting over will lose access to this session.",
  },
  headings: {
    eyebrow: "A small step. Real experience.",
    welcome: "Your first day, a different beginning.",
    greeting: (name: string) => `Welcome ${name}, let's get to work.`,
    tasks: "Pick your next task.",
    skills: "See how far you've come.",
    lead: "Learn by doing, not by watching. Every task brings you closer to confidence in your skills.",
  },
  catalogue: {
    title: "Your tasks",
    points: (points: number) => `${points} points`,
    passAt: (threshold: number) => `Pass at ${threshold}`,
    status: {
      available: "Available",
      in_progress: "In progress",
      completed: "Completed",
    } satisfies Record<TaskStatus, string>,
    action: {
      available: "Start task",
      in_progress: "Continue",
      completed: "Review task",
    } satisfies Record<TaskStatus, string>,
    comingSoon: "Coming soon",
    locked: "Locked",
    roadmap: "Up next on the roadmap",
    teasers: [
      {
        id: "sql-report",
        title: "SQL sales report",
        description: "Query the cleaned sales data and build the weekly report for management.",
      },
      {
        id: "client-email",
        title: "Client email",
        description: "Write a professional email explaining a delivery delay to an important client.",
      },
    ],
  },
  persona: {
    name: "Eng. Tarek",
    role: "Team Lead",
    intro: "Good morning! We have a sales file that needs reviewing before the report goes out. Focus on the details and take your time.",
    introSql: "The sales team needs a reliable regional report. Read the source data, write your query, and check the numbers.",
    introEmail: "A customer needs a clear update about a delayed order. Use the case facts and write a respectful response.",
  },
  mission: {
    title: "Your mission",
    steps: {
      "clean-sales": [
        "Download the raw sales file, in CSV or Excel.",
        "Clean it until every check below passes:",
        "Upload it, read the X-ray and Tarek's notes, and try again as often as you like.",
      ],
      "sql-report": [
        "Download the sales data and look at its columns.",
        "Write one SELECT query that gets these right:",
        "Submit it, read the X-ray and Tarek's notes, and try again as often as you like.",
      ],
      "client-email": [
        "Download the client case and note its exact facts.",
        "Write a reply that covers all of this:",
        "Submit it, read the X-ray and Tarek's notes, and try again as often as you like.",
      ],
    } satisfies Record<MissionTask, readonly [string, string, string]>,
    fullBrief: "Read the full brief",
  },
  workspace: {
    back: "Back to tasks",
    brief: "The brief",
    hints: "Hints (open if you need them)",
    checks: "How you'll be graded",
    critical: "Critical",
    points: (points: number) => `${points} pts`,
    passRule: (threshold: number) =>
      `Pass: ${threshold} points or more, and every critical check must pass.`,
    dataset: "Raw data file",
    datasetHint: "Download the file, clean it in Excel or Google Sheets, then upload it here.",
    sqlDatasetHint: "Download the sales data, inspect its columns, and write a SQL SELECT query in the editor below.",
    emailDatasetHint: "Download the client case and use its exact facts in your email below.",
    downloadCsv: "Download CSV",
    downloadXlsx: "Download XLSX",
    loading: "Loading the task…",
  },
  checks: {
    unique_orders: {
      title: "Unique orders",
      description: "Every order_id appears exactly once, with no blanks.",
    },
    standard_dates: {
      title: "Standard dates",
      description: "Every order_date uses the YYYY-MM-DD format.",
    },
    valid_numeric_values: {
      title: "Valid numbers",
      description: "Positive quantities and prices, and revenue equals quantity × unit price.",
    },
    complete_customer_records: {
      title: "Complete customer records",
      description: "Missing emails are marked “unavailable” instead of deleting rows.",
    },
    report_columns: { title: "Report columns", description: "Return region, paid_orders, and total_revenue." },
    paid_regions: { title: "Paid regions", description: "Include each region with paid sales exactly once." },
    paid_order_counts: { title: "Paid order counts", description: "Count the paid orders in each region." },
    paid_revenue: { title: "Paid revenue", description: "Calculate each region's paid revenue correctly." },
    recipient_and_subject: { title: "Recipient and subject", description: "Address the correct customer and identify the order." },
    case_facts: { title: "Case facts", description: "Use the correct order, dates, and refund amount." },
    action_plan: { title: "Action plan", description: "Apologize, explain the refund, and give a response window." },
    professional_closing: { title: "Professional closing", description: "Use a polite greeting, clear body, and company sign-off." },
  } satisfies Record<CheckId, CheckCopy>,
  upload: {
    title: "Ready to submit your work?",
    attempt: (n: number) => (n === 1 ? "First attempt" : `Attempt ${n}`),
    choose: "Choose the file you worked on",
    formats: (maxMb: number) => `CSV or XLSX · up to ${maxMb} MB`,
    sqlFormats: "SQL text (.sql)",
    emailFormats: "Plain text email (.txt)",
    sqlEditor: "Write your SQL SELECT query",
    emailEditor: "Write your client email",
    editorHint: "You can write here or choose a file below.",
    emptyEditor: "Write your answer or choose a file first.",
    encouragement: "Every attempt helps you understand more.",
    submit: "Submit for review",
    check: "Check result",
    completed: "This task is accepted. You can review the result and your skills profile.",
    another: "Choose another file",
  },
  processing: {
    title: "Eng. Tarek is reviewing your file",
    steps: ["File uploaded", "Running the four checks", "Writing feedback"],
  },
  result: {
    passTitle: "Great work! The file is solid.",
    passTitleGeneric: "Great work! Your submission passed.",
    failTitle: "Close, a few things need another look.",
    rejectedTitle: "The file was rejected before grading",
    score: "Score",
    success: (score: number) =>
      `Great work! You have successfully passed the assignment with a score of ${score} out of 100.`,
    failure: (score: number) =>
      `Deliverable did not meet passing requirements yet. Current score: ${score} out of 100. Review the supervisor feedback below to fix defects.`,
    retry:
      "You can revise the file and upload again anytime. Previous attempts are preserved with no score penalties.",
    criticalFailed: (score: number, threshold: number) =>
      `Your score is ${score}, which reaches the ${threshold}-point threshold, but the critical “Unique orders” check failed. Duplicate orders inflate sales figures, so the task can't pass until every order appears once.`,
    criticalFailedGeneric: (score: number, threshold: number) =>
      `Your score is ${score}, above the ${threshold}-point threshold, but a required check failed. Review the check details below and try again.`,
    passed: "Passed",
    failed: "Needs work",
    earned: (earned: number, total: number) => `${earned} of ${total}`,
    uploadRevision: "Upload revision",
    viewSkills: "View skills profile",
    checksTitle: "Check results",
  },
  insights: {
    impactTitle: "What this would cost the business",
    impactLead: "Measured on your own submission, by the same checks that set your score.",
    impactClear: "Nothing slipped through. As submitted, this work costs the business nothing.",
    metrics: {
      revenue_overstated: {
        label: "Revenue inflated by duplicate orders",
        hint: "Counted twice in the sales report if the file goes out as is.",
      },
      revenue_untrusted: {
        label: "Revenue sitting in broken rows",
        hint: "Quantities, prices or totals that don't add up.",
      },
      customers_unreachable: {
        label: "Customers the team can't contact",
        hint: "An invalid email, or no reason recorded for a missing one.",
      },
      orders_off_timeline: {
        label: "Orders that fall off the timeline",
        hint: "Dates outside YYYY-MM-DD can't be sorted or filtered.",
      },
      regions_misreported: {
        label: "Regions management would misread",
        hint: "Missing from the report, or carrying wrong numbers.",
      },
      customer_questions_left_open: {
        label: "Customer questions left open",
        hint: "Case facts or next steps the client still has to chase.",
      },
    } satisfies Record<MetricId, MetricCopy>,
    xrayTitle: "Mistake X-ray",
    xrayLead: "Every highlight points at your own work. The same rules that graded you found it.",
    loading: "Building your X-ray…",
    unavailable: "The detailed review isn't available right now.",
    retry: "Try again",
    table: {
      summary: (cells: number, rows: number) =>
        `${cells} ${cells === 1 ? "cell needs" : "cells need"} attention across ${rows} ${rows === 1 ? "row" : "rows"}.`,
      clean: "Every row passes every check.",
      filters: "Show issues for",
      all: "All checks",
      onlyIssues: "Only rows with issues",
      caption: "Your file, with every cell that failed a check highlighted",
      region: "Your file. Scroll sideways to see every column.",
      row: "Row",
      problems: "What's wrong",
      empty: "(empty)",
      alsoIn: (rows: string) => `same as row ${rows}`,
      showing: (shown: number, total: number) => `Showing ${shown} of ${total} rows.`,
      beyondPreview: (n: number) =>
        n === 1 ? "1 more issue is past the first 200 rows." : `${n} more issues are past the first 200 rows.`,
    },
    issues: {
      missing_order_id: "Order ID is empty",
      duplicate_order_id: "Duplicate order ID",
      nonstandard_date: "Date isn't YYYY-MM-DD",
      invalid_quantity: "Quantity isn't a positive whole number",
      invalid_unit_price: "Unit price is missing or negative",
      invalid_revenue: "Revenue is missing or negative",
      revenue_mismatch: "Revenue ≠ quantity × unit price",
      invalid_email: "Email address isn't valid",
      missing_email_reason: "Missing email has no “unavailable” note",
    } satisfies Record<IssueCode, string>,
    sql: {
      caption: "Your query's result, row by row",
      verdict: "Finding",
      empty: "Your query returned no rows.",
      columnsWrong: (columns: string) =>
        `Your result has the columns ${columns}. The report needs region, paid_orders and total_revenue, in that order.`,
      missing: (n: number) =>
        n === 1
          ? "1 paid region is missing from your result."
          : `${n} paid regions are missing from your result.`,
      robustnessTitle: "Hard-coded numbers detected",
      robustness:
        "We re-ran your query on a second copy of the sales data with a few extra orders, and your results didn't move with it. Compute every value from the sales table instead of typing it in.",
      region: {
        ok: "Paid region",
        unexpected: "Not a paid region",
        duplicate: "Listed twice",
        unreadable: "Can't read this row",
      } satisfies Record<RegionStatus, string>,
      countOk: "Count correct",
      countWrong: "Count wrong",
      revenueOk: "Revenue correct",
      revenueWrong: "Revenue wrong",
    },
    email: {
      text: "Your email, with what the reviewer found highlighted",
      checklist: "What the reviewer looked for",
      found: "Found",
      missing: "Missing",
      words: (count: number, min: number, max: number) =>
        `${count} words. Aim for ${min} to ${max}.`,
      elements: {
        recipient: "The customer's email on the To: line",
        subject_order: "Order number in the subject",
        body: "A message body",
        order_id: "Order number",
        promised_date: "Originally promised date",
        updated_date: "New delivery date",
        refund_amount: "Exact refund amount",
        apology: "An apology",
        refund: "The refund explained",
        response_window: "When they'll hear back",
        commitments_kept: "No promise taken back",
        greeting: "Greeting by name",
        closing_phrase: "A polite sign-off",
        company_signature: "Company signature",
        length: "A reasonable length",
      } satisfies Record<EmailElementId, string>,
    },
  },
  progress: {
    title: (attempt: number) => `Progress since attempt ${attempt}`,
    up: (points: number) => `+${points} points`,
    down: (points: number) => `${points} points`,
    same: "Same score",
    change: (before: string | number, after: string | number) => `${before} → ${after}`,
    wasRejected: "Last time the file was rejected before grading. This time every check ran.",
    status: { fixed: "Fixed", regressed: "New problem", open: "Still open" },
    issues: (before: number, after: number) => `${before} → ${after} issues`,
    cost: "What it costs the business now",
    chart: "Score by attempt",
    point: (attempt: number, score: number, passed: boolean) =>
      `Attempt ${attempt}: ${score}, ${passed ? "passed" : "not passed"}`,
    passMark: (threshold: number) => `Pass mark ${threshold}`,
    attempt: "Attempt",
    score: "Score",
    result: "Result",
    passed: "Passed",
    notPassed: "Not passed",
  },
  judge: {
    badge: "Judge mode",
    title: "Try it in one click",
    lead: "Each sample is uploaded and graded exactly like a learner's file. The label shows what the real evaluator gives it.",
    loading: "Loading samples…",
    outcome: {
      pass: (score: number) => `Pass · ${score}`,
      retry: (score: number) => `Retry · ${score}`,
      rejected: () => "Rejected before grading",
    },
    samples: {
      duplicates_left: {
        title: "Duplicates left in",
        note: "Everything fixed except repeated orders. Scores 75, yet the critical rule holds it back.",
      },
      half_done_excel: {
        title: "Half done, in Excel",
        note: "Duplicates and numbers fixed; dates and missing-email notes still wrong.",
      },
      column_deleted: {
        title: "A column deleted",
        note: "The learner removed missing_email_reason, so the file is refused before grading.",
      },
      fully_cleaned: { title: "Fully cleaned (Excel)", note: "Every check passes, from a typed Excel workbook." },
      hard_coded: {
        title: "Typed-in numbers",
        note: "Today's right totals, typed by hand. A second run on changed data exposes them.",
      },
      no_status_filter: { title: "Forgot the paid filter", note: "Counts pending and refunded orders as sales." },
      correct_query: { title: "Correct query", note: "Groups paid orders by region and computes from the table." },
      wrong_date_reply: {
        title: "One wrong date",
        note: "A polished reply with the wrong delivery date. Case facts are critical.",
      },
      vague_reply: { title: "Vague reply", note: "Wrong recipient, no facts, no plan." },
      complete_reply_en: {
        title: "Complete reply (English)",
        note: "Every fact, an apology, the refund and when they'll hear back.",
      },
      complete_reply_ar: { title: "Complete reply (Arabic)", note: "The same standard, in Egyptian Arabic." },
    } satisfies Record<SampleId, SampleCopy>,
    tour: {
      title: "Judge's tour",
      lead: "Five steps, about three minutes. Each one ticks itself off as you go.",
      progress: (done: number, total: number) => `${done} of ${total} done`,
      complete: "Tour complete. Everything you saw was graded live by the same deterministic checks.",
      go: "Take me there",
      done: "Done",
      current: "Next",
      steps: {
        mistake: {
          title: "See a mistake priced",
          hint: "In the sales task, submit “Duplicates left in”. Scroll to the X-ray and what it would cost.",
        },
        fix: { title: "Fix it and pass", hint: "Submit “Fully cleaned (Excel)” and watch the task complete." },
        sql: {
          title: "Catch hard-coded SQL",
          hint: "In the SQL task, submit “Typed-in numbers”. The query is re-run on changed data.",
        },
        email: {
          title: "Coach a client email",
          hint: "In the email task, submit “One wrong date”, then switch Tarek's feedback language.",
        },
        skills: { title: "See skills grow", hint: "Open Skills & progress: every point traces back to a check." },
      } satisfies Record<TourStep, StepCopy>,
    },
  },
  rejections: {
    unsupported_type: "Unsupported file type. Accepted formats are CSV or Excel (.xlsx) spreadsheets only.",
    artifact_too_large: "File size exceeds the limit shown for this task. Please reduce it and try again.",
    mime_mismatch:
      "File content does not match its extension. Please ensure the file is a valid spreadsheet.",
    expanded_size_exceeded:
      "The workbook is too large once unpacked. Save it as a plain spreadsheet without extra sheets or embedded objects.",
    sheet_limit_exceeded: "The workbook has more than one sheet, or more than 10,000 rows or 20 columns. Keep only the cleaned sheet.",
    artifact_unreadable:
      "Unable to read the file. Ensure the workbook is unencrypted, contains no macros and is saved as UTF-8.",
    missing_columns:
      "Required columns are missing. Keep all seven columns: order_id, customer_email, order_date, quantity, unit_price, revenue, missing_email_reason.",
    duplicate_columns: "The file has duplicate column names. Each column must appear once.",
    too_few_rows: "Fewer than 40 data rows remain. Remove duplicates only, not valid sales rows.",
    empty_file: "The file is empty. Choose the file you worked on.",
    unknown: "The file could not be graded. Check the format and try again.",
  } satisfies Record<RejectionCode | "unknown", string>,
  feedback: {
    title: "Supervisor feedback",
    fallback: "Direct alternative guidance generated from the local deterministic feedback system.",
    ai: "AI-written coaching. The score itself comes from deterministic checks.",
    toggle: "اعرض بالعربي",
    toggleLang: "ar",
    loading: "Preparing the other language…",
    sections: {
      decision: "Decision",
      impact: "Business impact",
      next: "Next action",
      score: "Score explanation",
    } satisfies Record<FeedbackSection, string>,
    listen: "Listen",
    stop: "Stop",
  },
  skills: {
    title: "Skills built through practice",
    names: {
      data_cleaning: "Data cleaning",
      attention_to_detail: "Attention to detail",
      sql_reporting: "SQL reporting",
      customer_communication: "Customer communication",
    } satisfies Record<SkillId, string>,
    basis: "Based on the recorded checks of your graded submissions.",
    empty:
      "No verified skills recorded yet. Complete your first practical assignment to populate verified competency evidence.",
    goToWork: "Go to Workplace",
    attempts: "Attempt timeline",
    attemptsCount: (n: number) => (n === 1 ? "1 recorded attempt" : `${n} recorded attempts`),
    attempt: (n: number) => `Attempt ${n}`,
    noAttempts: "No submissions yet. Your first attempt is the beginning.",
    viewResult: "View result",
    taskStatus: "Task status",
    retryPath: "Upload a revision",
  },
  journey: {
    title: "Your day today",
    steps: [
      { title: "Joined the team", hint: "Welcome to Yom Awel" },
      { title: "Work on your first task", hint: "Review, try, submit" },
      { title: "Record your first achievement", hint: "Watch your skills grow" },
    ],
    tipTitle: "Before you hit submit",
    tip: "Look at the file as the colleague who will use it. Are the numbers clear? Are the dates consistent? Every small detail matters.",
  },
  restart: {
    open: "Start over",
    title: "Are you sure you want to start over?",
    body: "This session has no account. Starting over creates a new session and you lose access to your current progress for good.",
    cancel: "Stay here",
    confirm: "Start over and lose access",
  },
};

export type Dictionary = typeof en;
