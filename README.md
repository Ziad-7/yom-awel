# 🚀 Yom Awel (يوم أول) — Workplace Simulation Platform

> **EUI GenAI for Education Hackathon 2026** (Student Track — AI Tutor Theme)  
> *Learn digital skills by getting hired into a simulated Egyptian tech company on Telegram.*

---

## 🎯 System Architecture & Shared Interfaces (The Contract)

To ensure all 5 AI agents build code that connects seamlessly without breaking, follow these exact shared function signatures and data schemas:

```
                  ┌───────────────────────────────┐
                  │   bot/telegram_app.py         │  <-- [Member 5]
                  │   (User interactions & files) │
                  └──────────────┬────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ core/            │   │ evaluators/      │   │ agents/          │
│ state_manager.py │   │ excel_evaluator  │   │ feedback_coach.py│
│ [Member 2]       │   │ [Member 4]       │   │ [Member 3]       │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

### 1. `core/state_manager.py` (Owner: Member 2)
```python
def get_or_create_user(user_id: str, name: str) -> dict:
    """Returns: {'user_id': str, 'name': str, 'current_day': int, 'active_task': str, 'status': str}"""

def get_current_task(user_id: str) -> dict:
    """Returns: {'task_id': str, 'title': str, 'description_ar': str, 'file_path': str}"""

def record_submission(user_id: str, task_id: str, passed: bool, code_score: int, soft_score: int, feedback: str) -> dict:
    """Records attempt, advances current_day if passed, updates skills record.
    Returns: {'status': 'updated', 'next_task': str, 'current_day': int}"""

def get_user_skills_profile(user_id: str) -> dict:
    """Returns: {'user_id': str, 'skills': {'data_cleaning': 85, 'sql': 70}, 'badges': list}"""
```

### 2. `evaluators/excel_evaluator.py` (Owner: Member 4)
```python
def evaluate_sales_cleaning(submitted_file_path: str) -> dict:
    """
    Evaluates submitted CSV/Excel against data hygiene rules.
    Returns EXACTLY:
    {
        "passed": True / False,            # True if score >= 75
        "score": int,                     # 0 to 100
        "details": {
            "duplicates_removed": bool,
            "negatives_fixed": bool,
            "dates_standardized": bool,
            "missing_handled": bool
        },
        "errors": list[str],              # e.g. ["3 negative prices remain"]
        "summary_ar": str,                # Short Arabic explanation
        "summary_en": str
    }
    """
```

### 3. `agents/feedback_coach.py` (Owner: Member 3)
```python
def generate_pedagogical_feedback(task_name: str, deterministic_result: dict, student_message: str = "") -> str:
    """
    Takes the deterministic evaluation dict from Member 4 and generates Eng. Tarek's
    realistic Egyptian workplace coaching response.
    Returns: str (Egyptian Arabic text message)
    """
```

### 4. `bot/telegram_app.py` (Owner: Member 5)
* Calls `core.state_manager.get_or_create_user()` on `/start`.
* Sends the sample dirty file from `data/sales_dirty.csv`.
* When a file is received:
  1. Calls `evaluators.excel_evaluator.evaluate_sales_cleaning()`.
  2. Passes result to `agents.feedback_coach.generate_pedagogical_feedback()`.
  3. Calls `core.state_manager.record_submission()`.
  4. Replies to the user with Tarek's feedback + updated score.

---

## 🛠️ Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <REPO_URL>
   cd yom-awel
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set your API Keys (in `.env`):**
   ```env
   TELEGRAM_BOT_TOKEN="your_token_from_botfather"
   GEMINI_API_KEY="your_gemini_key_or_openai"
   ```
4. **Read your task in `TEAM_PROMPTS.md`!**
