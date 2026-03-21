"""Regression guards for the GitHub CI workflow."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_ci_workflow() -> dict[str, Any]:
    workflow_path = _repo_root() / ".github" / "workflows" / "ci.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def _job_steps(job: dict[str, Any]) -> Iterable[dict[str, Any]]:
    steps = job.get("steps")
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]
    return []


def _jobs_running_alembic_upgrade(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return {}

    matched_jobs: dict[str, dict[str, Any]] = {}
    for job_name, raw_job in jobs.items():
        if not isinstance(raw_job, dict):
            continue

        for step in _job_steps(raw_job):
            run_block = step.get("run")
            if not isinstance(run_block, str):
                continue
            if "uv run alembic upgrade head" in run_block:
                matched_jobs[str(job_name)] = raw_job
                break

    return matched_jobs


def _step_by_name(job: dict[str, Any], step_name: str) -> dict[str, Any]:
    for step in _job_steps(job):
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Step {step_name!r} not found")


def test_ci_jobs_running_alembic_should_define_required_env() -> None:
    workflow = _load_ci_workflow()
    required_env = {"SECRET_KEY", "PHASE4_TENANT_NOT_NULL_DECISION"}

    missing_by_job: dict[str, list[str]] = {}
    for job_name, job in _jobs_running_alembic_upgrade(workflow).items():
        env = job.get("env")
        if not isinstance(env, dict):
            missing_by_job[job_name] = sorted(required_env)
            continue

        missing = sorted(required_env.difference(env))
        if missing:
            missing_by_job[job_name] = missing

    assert not missing_by_job, (
        "Jobs that initialize databases via Alembic must declare CI-safe env values: "
        f"{missing_by_job}"
    )


def test_frontend_coverage_gate_should_follow_vitest_artifact_paths() -> None:
    workflow = _load_ci_workflow()
    frontend_job = workflow["jobs"]["frontend-test"]

    coverage_step = _step_by_name(frontend_job, "Check coverage threshold")
    coverage_script = str(coverage_step.get("run", ""))
    expected_summary_path = "../test-results/frontend/coverage/coverage-summary.json"

    assert expected_summary_path in coverage_script
    assert "fs.readFileSync('coverage/coverage-summary.json'" not in coverage_script
    assert "\n  coverage/coverage-summary.json \\\n" not in coverage_script

    upload_step = _step_by_name(frontend_job, "Upload frontend reports")
    upload_config = upload_step.get("with")
    assert isinstance(upload_config, dict)
    upload_path = str(upload_config.get("path", ""))

    assert "test-results/frontend/coverage/" in upload_path
    assert "test-results/frontend/reports/" in upload_path
    assert "\n          frontend/coverage/\n" not in upload_path
    assert "\n          frontend/test-results.json\n" not in upload_path
