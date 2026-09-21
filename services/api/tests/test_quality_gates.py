from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_pre_commit_config() -> None:
    config_path = ROOT / ".pre-commit-config.yaml"
    assert config_path.exists()

    config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    repos = config.get("repos", [])
    local_hooks = []
    for repo in repos:
        if repo.get("repo") == "local":
            local_hooks.extend(repo.get("hooks", []))

    assert local_hooks, "Should have local hooks"

    hook_ids = {hook["id"] for hook in local_hooks}
    assert "ruff-format" in hook_ids
    assert "ruff-lint" in hook_ids
    assert "mypy" in hook_ids
    assert "pytest" in hook_ids


def test_ci_workflow() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    assert workflow_path.exists()

    workflow: dict[str, Any] = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    # Account for YAML 1.1 parsing of 'on' becoming True
    trigger = workflow.get(True) or workflow.get("on")
    assert trigger is not None, "Workflow must have 'on' triggers"
    assert "push" in trigger
    assert "pull_request" in trigger

    # Prove unrestricted triggers
    assert trigger["push"] is None or not trigger["push"].get("branches")
    assert trigger["pull_request"] is None or not trigger["pull_request"].get("branches")

    jobs = workflow.get("jobs", {})
    assert "quality" in jobs
    quality_job = jobs["quality"]

    # Check permissions
    perms = quality_job.get("permissions", {})
    assert perms.get("contents") == "read"

    # Check runs-on
    assert "ubuntu" in quality_job.get("runs-on", "")

    steps = quality_job.get("steps", [])

    commands_found = set()
    for step in steps:
        step_str = str(step)
        assert "secrets." not in step_str
        assert "deploy" not in step_str.lower()
        assert "vercel" not in step_str.lower()
        assert "aws" not in step_str.lower()

        # Check action versions
        uses = step.get("uses", "")
        if uses.startswith("actions/checkout"):
            assert uses == "actions/checkout@v7"
        if uses.startswith("astral-sh/setup-uv"):
            assert uses == "astral-sh/setup-uv@v10"
        if uses.startswith("actions/setup-python"):
            assert uses == "actions/setup-python@v6"
            assert "3.12" in step.get("with", {}).get("python-version", "")

        run = step.get("run", "")
        if "pre-commit" in run:
            commands_found.add("pre-commit")
        if "pytest" in run:
            commands_found.add("pytest")
        if "mypy" in run:
            commands_found.add("mypy")
        if "ruff format" in run:
            commands_found.add("ruff format")
        if "ruff check" in run:
            commands_found.add("ruff check")
        if "git diff --exit-code" in run:
            commands_found.add("diff")
        if "export_schemas.py" in run:
            commands_found.add("export_schemas")
        if "uv lock --check" in run:
            commands_found.add("uv lock")
        if "uv sync" in run:
            assert "--locked" in run
            assert "--group dev" in run
            commands_found.add("uv sync")

    assert "pre-commit" in commands_found
    assert "pytest" in commands_found
    assert "mypy" in commands_found
    assert "ruff format" in commands_found
    assert "ruff check" in commands_found
    assert "diff" in commands_found
    assert "export_schemas" in commands_found
    assert "uv lock" in commands_found
    assert "uv sync" in commands_found
