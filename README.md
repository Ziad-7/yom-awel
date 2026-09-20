# Yom Awel (يوم أول)

Workplace simulation engine for task-based digital skills training.

---

## Overview

Yom Awel trains entry-level digital and technical skills through workplace simulations rather than passive video lectures or multiple-choice quizzes. The learner interacts with an automated organization via Telegram, receiving practical tasks (spreadsheet cleaning, SQL query development, business communication) from simulated colleagues and managers.

Submissions are evaluated through a two-stage pipeline:
1. **Deterministic Verification:** Automated unit checks (via `pandas`, `openpyxl`, or `sqlite3`) inspect submitted artifacts for correctness, schema adherence, and data integrity.
2. **Pedagogical Feedback:** An LLM agent generates constructive, contextual feedback in Egyptian workplace Arabic based on the deterministic test results.

User progress is persisted in a local state store that tracks completed tasks and generates a competency profile.

---

## System Architecture

```
                               ┌───────────────────────────┐
                               │     bot/telegram_app.py   │
                               │  (Telegram Client Layer)  │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       │                     │                     │
                       ▼                     ▼                     ▼
             ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
             │ core/            │  │ evaluators/      │  │ agents/          │
             │ state_manager.py │  │ excel_evaluator  │  │ feedback_coach.py│
             │ (State & DB)     │  │ (Unit Checks)    │  │ (LLM Feedback)   │
             └──────────────────┘  └──────────────────┘  └──────────────────┘
                                             ▲
                                             │
                                   ┌─────────┴─────────┐
                                   │ data/             │
                                   │ sales_dirty.csv   │
                                   └───────────────────┘
```

### Module Responsibilities
- `core/`: State management, user tracking, task progression, and skill scoring.
- `evaluators/`: Deterministic artifact evaluation scripts for tabular data, spreadsheets, and database queries.
- `agents/`: LLM persona definitions and feedback generation prompts.
- `bot/`: Telegram bot service handling incoming messages, file transfers, and user state routing.
- `data/`: Sample datasets, evaluation benchmarks, and task seed files.

---

## Module Interfaces

Components communicate using the following interfaces:

### 1. `core.state_manager`
```python
def get_or_create_user(user_id: str, name: str) -> dict:
    """Retrieve or initialize a user record.
    Returns: {'user_id': str, 'name': str, 'current_day': int, 'active_task': str, 'status': str}
    """

def get_current_task(user_id: str) -> dict:
    """Retrieve details and files for the user's active task.
    Returns: {'task_id': str, 'title': str, 'description_ar': str, 'file_path': str}
    """

def record_submission(user_id: str, task_id: str, passed: bool, code_score: int, soft_score: int, feedback: str) -> dict:
    """Record an evaluation attempt, update competency scores, and advance task state if passed."""

def get_user_skills_profile(user_id: str) -> dict:
    """Retrieve aggregate scores across skill categories."""
```

### 2. `evaluators.excel_evaluator`
```python
def evaluate_sales_cleaning(submitted_file_path: str) -> dict:
    """Validate submitted CSV/Excel against benchmark constraints.
    Returns:
    {
        "passed": bool,
        "score": int,              # 0 to 100
        "details": dict,           # {duplicates_removed: bool, negatives_fixed: bool, ...}
        "errors": list[str],       # Specific validation errors
        "summary_ar": str,         # Brief explanation in Arabic
        "summary_en": str          # Brief explanation in English
    }
    """
```

### 3. `agents.feedback_coach`
```python
def generate_pedagogical_feedback(task_name: str, deterministic_result: dict, student_message: str = "") -> str:
    """Generate contextual feedback in Egyptian workplace Arabic based on evaluation output."""
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Telegram Bot Token (from `@BotFather`)
- Google Gemini or OpenAI API Key

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/Ziad-7/yom-awel.git
   cd yom-awel
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file in the project root:
   ```env
   TELEGRAM_BOT_TOKEN="your_token_here"
   GEMINI_API_KEY="your_api_key_here"
   ```

4. Start the bot:
   ```bash
   python bot/telegram_app.py
   ```

---

## Team Responsibilities

- **Member 1 (`submission/`):** Submission documentation, pitch deck, and application forms.
- **Member 2 (`core/`):** State machine, user progression, and SQLite persistence.
- **Member 3 (`agents/`):** Persona prompt engineering and LLM feedback generation.
- **Member 4 (`evaluators/`, `data/`):** Test datasets and deterministic evaluation scripts.
- **Member 5 (`bot/`):** Telegram bot routing, file I/O, and integration testing.
