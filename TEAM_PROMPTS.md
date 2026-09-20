# 🚀 Yom Awel (يوم أول) — Team AI Agent Prompts & Architecture Guide

> **Project:** Yom Awel (يوم أول) — Learn digital skills by getting a simulated job on Telegram / WhatsApp.  
> **Target:** EUI GenAI for Education Hackathon 2026 (Student Track, AI Tutor Theme, Best Arabic Solution).  
> **Deadline:** Tonight, September 20, 2026!

---

## 📂 Proposed Repository Structure

To ensure the 5 of you can work in parallel **without git merge conflicts**, use this directory structure:

```
yom-awel/
├── requirements.txt
├── README.md
├── data/                      <-- [Member 4] Sample dirty spreadsheets, SQL schemas
│   ├── sales_dirty.csv
│   └── test_queries.sql
├── core/                      <-- [Member 2] State Machine & DB
│   ├── __init__.py
│   ├── db.py
│   └── state_manager.py
├── agents/                    <-- [Member 3] LLM Personas & Prompts
│   ├── __init__.py
│   ├── llm_client.py
│   ├── personas.py
│   └── feedback_coach.py
├── evaluators/                <-- [Member 4] Deterministic Graders
│   ├── __init__.py
│   ├── excel_evaluator.py
│   └── sql_evaluator.py
├── bot/                       <-- [Member 5] Telegram Bot / Web Interface
│   ├── __init__.py
│   ├── telegram_app.py
│   └── web_simulator.py
└── submission/                <-- [Member 1] Form Answers & Pitch Deck
    ├── form_answers.md
    └── pitch_deck.md
```

---

## 📋 Member 1: Team Lead — Pitch Deck & Form Submission

**Copy & Paste this prompt into your AI Agent:**

```text
You are an expert EdTech startup pitch advisor and copywriter for top accelerator competitions (like EdVentures and Y Combinator). 

We are competing in the EUI GenAI for Education Hackathon 2026 (Student Track, AI Tutor Theme) with our project called "Yom Awel" (يوم أول).

### Project Overview:
"Yom Awel" inverts online learning. Instead of opening a course, the learner gets hired into a simulated Egyptian tech company via Telegram/WhatsApp. An AI Manager (Eng. Tarek) messages them in Egyptian Arabic with realistic workplace tasks (cleaning dirty client spreadsheets, fixing SQL queries, writing professional emails). Multiple AI personas (Manager, Colleague, Client) interact with them. Submissions are real files (Excel, SQL) evaluated by a hybrid engine: deterministic code checks (pandas/openpyxl) + LLM pedagogical rubric. As they complete tasks, an adaptive skills knowledge graph builds a verified skills record for employers.

### Your Task:
Please generate two complete, publication-ready deliverables:

1. THE EDVENTURES APPLICATION FORM RESPONSES:
Provide rich, high-scoring answers ready to copy-paste into each official field:
- Team Name: Yom Awel (يوم أول)
- Thematic Challenge: AI Tutor (Personalized tutoring for STEM, ICT, & employability)
- Problem Statement (200-250 words): Focus on Egypt's 1.3M youth entering the job market, 78% employer skills gap, the failure of passive MOOCs/quizzes, and the lack of workplace experience.
- Target User / Beneficiary: Undergrads, fresh grads, and career switchers looking for entry-level data/digital jobs.
- Evidence & Validation: Egyptian employer reports, tech talent shortages, student frustration with theoretical tutorials.
- Solution Overview: Detailed breakdown of the workplace simulation, multi-agent group dynamics, and verified skills portfolio.
- How is Generative AI used & Why is it necessary?: Detail the role of multi-agent LLMs (Manager, Client, Peer) for dynamic conversation, adaptive difficulty, and personalized soft-skill coaching combined with deterministic validation.
- Current Development Stage: Working prototype / MVP.

2. COMPLETE 10-SLIDE PITCH DECK CONTENT:
Provide slide-by-slide text, headlines, bullets, visual suggestions, and a 30-second speaker script for each slide:
- Slide 1: Cover (Hook, Tagline, Team)
- Slide 2: The Problem (The Employability Paradox in Egypt)
- Slide 3: The Insight (You don't learn to work from a video; you learn by doing real work)
- Slide 4: The Solution: "Yom Awel" (Workplace Simulation on Telegram)
- Slide 5: The Secret Sauce: Dual-Layer Engine (Deterministic Code Checker + LLM Pedagogical Coach)
- Slide 6: The User Journey (Day 1 Onboarding -> Task Delivery -> Feedback -> Skills Card)
- Slide 7: Market Opportunity & Alignment with MCIT / GAINAfrica
- Slide 8: Business Model (B2C subscriptions, B2B talent pipeline for Egyptian companies)
- Slide 9: The 24-Hour Prototype & Live Demo Architecture
- Slide 10: The Team & Vision (Why we can build this)

Make the tone confident, visionary, professional, and culturally resonant with Egyptian tech education.
```

---

## ⚙️ Member 2: Backend Specialist — Core State Machine & User Progress

**Copy & Paste this prompt into your AI Agent:**

```text
You are a Senior Python Backend Engineer. 

You are building the core state engine for "Yom Awel" (يوم أول), a workplace simulation platform where learners receive daily workplace tasks over chat (Telegram/WhatsApp).

### Requirements:
1. Implement a lightweight SQLite-backed (or pure Python class with SQLite persistence) State Manager in `core/state_manager.py`.
2. Model the following entities:
   - User: `user_id` (str/int), `full_name`, `joined_at`, `current_day` (int, default 1), `active_task_id`, `status` (ONBOARDING, IN_TASK, SUBMITTED, COMPLETED).
   - Task Catalog: Predefined dictionary/table of tasks:
     * Task 1: "clean_sales_data" (Excel data hygiene)
     * Task 2: "fix_customer_sql" (SQL query debugging)
     * Task 3: "client_escalation_email" (Professional communication)
   - User Task Attempt: `user_id`, `task_id`, `attempt_number`, `code_score`, `soft_skill_score`, `passed` (bool), `feedback_text`, `submitted_at`.
   - Verified Skills Record: Running score for skills like `data_cleaning`, `sql_querying`, `business_communication`, `attention_to_detail` (0-100%).

3. Core Methods to Implement:
   - `get_or_create_user(user_id, name)` -> User dict
   - `get_current_task(user_id)` -> Task details, instructions, sample download path
   - `record_submission(user_id, task_id, passed, code_score, soft_score, feedback)` -> Updates attempt, adjusts skills record, advances `current_day` if passed.
   - `get_user_skills_profile(user_id)` -> Returns a formatted summary of completed tasks, badges, and skill percentages.
   - `reset_user(user_id)` -> For demo reset testing.

4. Deliverable:
Provide clean, robust, well-typed Python code with a `if __name__ == "__main__":` test block demonstrating creating a user, assigning Task 1, recording a passed submission, and displaying their updated skills profile.
```

---

## 🤖 Member 3: AI Persona & Agent Engineer — Egyptian Personas & Feedback Coach

**Copy & Paste this prompt into your AI Agent:**

```text
You are an expert AI Prompt Engineer and Python Developer specializing in LLM Agent Orchestration.

You are creating the conversational personas and feedback agents for "Yom Awel" (يوم أول), an Egyptian workplace simulation platform.

### Requirements:
Build `agents/personas.py` and `agents/feedback_coach.py` using Python and Google Gemini API (`google-genai` or `google-generativeai`) or standard OpenAI-compatible client (using free tier / API key from env `GEMINI_API_KEY` or `OPENAI_API_KEY`).

1. PERSONAS (System Prompts in authentic, professional Egyptian tech workplace Arabic):
   - **Eng. Tarek (المهندس طارق - مدير الداتا):**
     * Personality: Busy, professional, direct, doesn't like excuses, but genuinely wants to mentor promising juniors. Speaks Egyptian Arabic mixed with common tech terms ("يا بطل", "شيت الإكسل ده", "الـ client مستني", "الكود مش optimized").
     * Role: Delivers the daily task, asks for status updates, and delivers final acceptance or rejection.
   - **Hazem (حازم - الزميل اللطيف):**
     * Personality: Helpful, slightly informal colleague who joined 6 months ago. Gives hints without solving the whole problem if the user is stuck.
   - **Mona (منى - مسؤولة العلاقات مع العملاء / العميل):**
     * Personality: Stressed, urgent, asks why numbers don't match.

2. THE FEEDBACK COACH AGENT (`feedback_coach.py`):
   - Function: `generate_pedagogical_feedback(task_name, deterministic_result, student_message, language="ar") -> str`
   - Takes:
     * `task_name`: e.g. "Data Cleaning on Sales Excel"
     * `deterministic_result`: Dict from the code evaluator (e.g. `{"passed": False, "score": 60, "errors": ["3 duplicate rows remained", "Negative revenue in row 14"]}`)
     * `student_message`: The student's text message accompanying the file.
   - Outputs:
     * A structured, realistic reply from Eng. Tarek in Egyptian Arabic:
       1. First reaction (whether approved or needs rework).
       2. Constructive explanation of *why* the error matters in business (e.g. "لو بعتنا الأرقام دي للـ CFO هيحصل دروب").
       3. A targeted tip on how to fix it.
       4. Score breakdown.

3. Deliverable:
Provide `personas.py`, `feedback_coach.py`, and a standalone test script that calls the Gemini/OpenAI API with a simulated failed Excel evaluation and prints Tarek's Arabic response.
```

---

## 🧪 Member 4: Deterministic Grader & Sample Task Creator

**Copy & Paste this prompt into your AI Agent:**

```text
You are a Senior Python Data Engineer and QA Specialist.

In "Yom Awel" (يوم أول), we evaluate learners' work using deterministic Python code checks BEFORE feeding the results to an LLM. This guarantees 100% reliable grading without LLM hallucinations.

### Your Tasks:
1. CREATE SAMPLE DIRTY DATA (`data/sales_dirty.csv` and `data/create_sample_data.py`):
   - Create a realistic 50-row sales dataset with intentionally planted beginner errors:
     * 5 exact duplicate customer purchase rows.
     * 3 rows with negative values in the `revenue` / `quantity` columns.
     * 4 rows with messy dates (`2026/08/12`, `12-08-2026`, invalid strings).
     * Missing values in `customer_email`.
   - Write `create_sample_data.py` so anyone on the team can run it to generate `sales_dirty.csv` and `sales_clean_solution.csv`.

2. WRITE THE EXCEL/CSV EVALUATOR (`evaluators/excel_evaluator.py`):
   - Implement `evaluate_sales_cleaning(submitted_file_path: str) -> dict`:
     * Checks if file exists and can be parsed by `pandas`.
     * Check 1: Were all 5 duplicates removed? (+25 pts)
     * Check 2: Were negative values fixed or dropped? (+25 pts)
     * Check 3: Are dates standardized to `YYYY-MM-DD`? (+25 pts)
     * Check 4: Were missing values handled appropriately? (+25 pts)
     * Returns a dictionary:
       ```python
       {
           "passed": True / False,  # True if score >= 75
           "score": int,           # 0 to 100
           "details": {
               "duplicates_removed": True,
               "negatives_fixed": False,
               "dates_standardized": True,
               "missing_handled": True
           },
           "errors": ["3 negative values still exist in column 'Price'"],
           "summary_en": "Good job on deduplication, but check column Price for negative numbers.",
           "summary_ar": "شغلك كويس في شيل التكرارات، بس لسه فيه أرقام بالسالب في عمود السعر."
       }
       ```

3. WRITE A BASIC SQL EVALUATOR (`evaluators/sql_evaluator.py`):
   - Implement `evaluate_sql_query(student_query: str, target_task: str) -> dict`:
     * Uses in-memory `sqlite3` populated with a mini 2-table schema (`customers` and `orders`).
     * Compares student query output against the reference query output.
     * Returns score, matched rows, error messages.

4. Deliverable:
Provide `create_sample_data.py`, `excel_evaluator.py`, `sql_evaluator.py`, and a test script verifying that submitting a dirty file fails and a clean file passes with 100/100.
```

---

## 📱 Member 5: Bot Integration & Demo Video Creator

**Copy & Paste this prompt into your AI Agent:**

```text
You are a Fullstack Python Developer experienced with `python-telegram-bot` and rapid prototyping.

You are responsible for the user-facing interface of "Yom Awel" (يوم أول): creating the Telegram Bot and a lightweight Web fallback so judges can experience the simulation.

### Requirements:
1. TELEGRAM BOT (`bot/telegram_app.py`):
   - Uses `python-telegram-bot` (v20+ async).
   - Commands & Flow:
     * `/start`: Welcome message from "Eng. Tarek" welcoming the new hire on their first day at "Horizon Tech Egypt" in Egyptian Arabic.
     * Bot automatically sends Task 1: Attaches `sales_dirty.csv` with a voice/text note explaining: "صباح الخير يا باشمهندس، مبروك انضمامك للتيم. الشيت ده مبعوت من فرع إسكندرية وفيه داتا ضاربة. نضفه وابعتلي النسخة النظيفة هنا قبل الساعة ٢."
     * Document Handler: When user replies with a document (`.csv` or `.xlsx`):
       - Downloads the file locally.
       - Calls Member 4's `evaluate_sales_cleaning()`.
       - Calls Member 3's `generate_pedagogical_feedback()`.
       - Calls Member 2's `record_submission()`.
       - Sends back Tarek's Arabic feedback + updated skills score!
     * `/status` or `/skills`: Displays the user's verified digital skills badge and probation level.

2. LIGHTWEIGHT WEB SIMULATOR (Fallback in `bot/web_simulator.py` or Streamlit):
   - A single-file Streamlit or FastAPI/HTML app that simulates the exact same chat for judges who don't have Telegram open on desktop.
   - Includes a direct button: "👉 Open in Telegram (@YomAwelBot)".

3. 90-SECOND DEMO VIDEO CHECKLIST:
   - Provide a step-by-step script for recording a 90-second Loom/YouTube walkthrough:
     * [0:00 - 0:20]: Show the Telegram bot receiving the /start command and Eng. Tarek's Egyptian welcome.
     * [0:20 - 0:45]: Download the dirty spreadsheet, show the error, submit it back.
     * [0:45 - 1:15]: Show the deterministic checker running, followed by Tarek's contextual Egyptian audio/text feedback.
     * [1:15 - 1:30]: Show the updated verified skills profile ready for employers.

4. Deliverable:
Provide `telegram_app.py`, `web_simulator.py`, instructions to get a free Telegram Bot token from `@BotFather`, and how to run it locally.
```
