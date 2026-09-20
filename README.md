# 🏢 Yom Awel (يوم أول)
### *Workplace Simulation Engine for Active Digital Skills Learning*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Telegram%20%7C%20Web-2CA5E0.svg)](https://telegram.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **"Don't take a course. Get hired."**  
> Yom Awel inverts online education: instead of watching videos and answering multiple-choice quizzes, learners are placed inside a simulated Egyptian corporate office where they complete real-world tasks under realistic workplace pressure.

---

## 💡 The Problem

Every year, over **1.3 million youth** enter the Egyptian job market, yet **78% of employers** report struggling to find candidates with job-ready practical skills. Traditional online courses fail because:
* They teach theoretical syntax in isolation without workplace context.
* Multiple-choice questions (MCQs) cannot assess messy problem-solving.
* Beginners freeze on day one when given dirty corporate data, ambiguous requirements, or demanding client feedback.

---

## 🚀 The Solution

**Yom Awel** simulates the first 30 days of an entry-level tech job (Data Analyst, Junior Developer, or IT Specialist) directly inside **Telegram**:

1. **You Get Hired:** You join a simulated company ("Horizon Tech Egypt") and are placed in a team group chat.
2. **Real Tasks, Not Quizzes:** At 9:00 AM, your AI Manager (**Eng. Tarek**) messages you in authentic Egyptian workplace Arabic with real messy files:
   * *"Clean this corrupted regional sales spreadsheet before 2 PM."*
   * *"Write the SQL query for this inventory anomaly report."*
   * *"Reply to this angry corporate client professionally."*
3. **Dynamic Workplace Drama:** AI colleagues (**Hazem**) and AI clients (**Mona**) message the group, alter requirements, ask for status updates, or give helpful tips.
4. **Dual-Layer Evaluation:** When you submit your file (`.xlsx`, `.csv`, `.sql`):
   * **Deterministic Layer:** Python scripts (`pandas`, `openpyxl`, `sqlite3`) test whether you actually fixed the data or query with 100% mathematical accuracy.
   * **LLM Pedagogical Layer:** Eng. Tarek reviews your communication and reasoning, explaining *why* your errors matter to the business and how to improve.
5. **Verified Skills Record:** Every approved submission updates your verifiable, employer-facing skills graph.

---

## 🏗️ System Architecture

```
                               ┌───────────────────────────┐
                               │     bot/telegram_app.py   │
                               │  (Telegram Chat Interface)│
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       │                     │                     │
                       ▼                     ▼                     ▼
             ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
             │ core/            │  │ evaluators/      │  │ agents/          │
             │ state_manager.py │  │ excel_evaluator  │  │ feedback_coach.py│
             │ (User Day & DB)  │  │ (Code Checks)    │  │ (LLM Personas)   │
             └──────────────────┘  └──────────────────┘  └──────────────────┘
                                             ▲
                                             │
                                   ┌─────────┴─────────┐
                                   │ data/             │
                                   │ sales_dirty.csv   │
                                   └───────────────────┘
```

### Module Breakdown:
* **`core/`**: SQLite-backed state machine tracking the user's current day, active tasks, attempt history, and dynamic skills record.
* **`evaluators/`**: Deterministic unit-test checkers that validate student artifacts (`.csv`, `.xlsx`, `.sql`) without LLM hallucination risk.
* **`agents/`**: Conversational multi-agent personas engineered in natural Egyptian workplace dialect (Manager, Colleague, Client) + pedagogical coaching rubric.
* **`bot/`**: Telegram Bot polling and webhook handlers + document upload/download management.
* **`data/`**: Planted workplace artifacts (corrupted spreadsheets, raw database dumps, customer support tickets).

---

## ⚙️ Shared Interface Contract

To keep all components decoupled and modular, modules interact through these exact function signatures:

### 1. `core.state_manager`
```python
def get_or_create_user(user_id: str, name: str) -> dict:
    """Returns: {'user_id': str, 'name': str, 'current_day': int, 'active_task': str, 'status': str}"""

def get_current_task(user_id: str) -> dict:
    """Returns: {'task_id': str, 'title': str, 'description_ar': str, 'file_path': str}"""

def record_submission(user_id: str, task_id: str, passed: bool, code_score: int, soft_score: int, feedback: str) -> dict:
    """Records attempt, updates running skills, advances day if passed."""

def get_user_skills_profile(user_id: str) -> dict:
    """Returns: {'user_id': str, 'skills': {'data_cleaning': 85, 'sql': 70}, 'badges': list}"""
```

### 2. `evaluators.excel_evaluator`
```python
def evaluate_sales_cleaning(submitted_file_path: str) -> dict:
    """
    Returns:
    {
        "passed": bool,
        "score": int,              # 0 - 100
        "details": dict,           # {duplicates_removed: bool, negatives_fixed: bool, ...}
        "errors": list[str],
        "summary_ar": str,
        "summary_en": str
    }
    """
```

### 3. `agents.feedback_coach`
```python
def generate_pedagogical_feedback(task_name: str, deterministic_result: dict, student_message: str = "") -> str:
    """Generates Eng. Tarek's constructive Arabic feedback based on the deterministic evaluation."""
```

---

## 🚀 Quickstart & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Ziad-7/yom-awel.git
cd yom-awel
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_from_botfather"
GEMINI_API_KEY="your_gemini_or_openai_api_key"
```

### 4. Run the Telegram Bot
```bash
python bot/telegram_app.py
```

---

## 👥 Team & Contributing

* **Member 1:** Pitch & Product Strategy (`submission/`)
* **Member 2:** State Machine & Database Engine (`core/`)
* **Member 3:** AI Personas & Feedback Agents (`agents/`)
* **Member 4:** Deterministic Graders & Datasets (`evaluators/`, `data/`)
* **Member 5:** Bot Interface & Demo Integration (`bot/`)

For individual agent implementation instructions, refer to [**TEAM_PROMPTS.md**](./TEAM_PROMPTS.md).
