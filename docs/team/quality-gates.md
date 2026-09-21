# Quality Gates & CI

To ensure repository hygiene and contract adherence, this project uses deterministic local hooks and GitHub Actions.

## Local setup

We use `pre-commit` managed via `uv` to ensure consistent formatting, typing, and tests without requiring global tool installations. 

To install the hooks locally:
```bash
# 1. Ensure you have synced the environment
cd services/api && uv sync --locked --group dev

# 2. Install pre-commit hooks to run automatically before every commit
uv run --project services/api pre-commit install
```

## Running quality checks manually

To match the CI environment locally, run the following command to execute all hooks across all files:
```bash
uv run --project services/api pre-commit run --all-files
```

This will run:
- **Ruff format check**: Verifies code formatting.
- **Ruff lint**: Checks for linting errors.
- **Strict mypy**: Ensures strict type-checking in `src/yom_awel`.
- **Pytest**: Runs the full test suite.

Note: Hooks do not modify your files automatically (e.g. `ruff format` runs in `--check` mode). If the formatting check fails, it will fail clearly and you should format your files by running:
```bash
uv run --project services/api ruff format
```

## Continuous Integration (CI)

A GitHub Actions workflow (`ci.yml`) is triggered on **every push to any branch** and **every pull request**.
It runs with least-privilege `contents: read` permissions on Ubuntu with Python 3.12. 
It guarantees zero hidden costs (no paid services, no secrets required). 

In addition to the pre-commit hooks, CI runs:
- `uv lock --check`: Ensures `uv.lock` is up-to-date with `pyproject.toml`.
- Schema exports & `git diff --exit-code`: Ensures that generated schemas are always committed and match the contract models.
