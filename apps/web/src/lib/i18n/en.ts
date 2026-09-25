import type { CheckId, RejectionCode, SkillId, TaskStatus } from "./keys";

type CheckCopy = { title: string; description: string };

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
