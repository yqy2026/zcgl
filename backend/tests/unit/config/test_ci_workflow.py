"""Regression guards for the GitHub CI workflow."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_ci_workflow() -> dict[str, Any]:
    workflow_path = _repo_root() / ".github" / "workflows" / "ci.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def _load_workflow(workflow_name: str) -> dict[str, Any]:
    workflow_path = _repo_root() / ".github" / "workflows" / workflow_name
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


def test_e2e_jobs_should_use_dedicated_test_database_names() -> None:
    workflow = _load_ci_workflow()
    expected_database_names = {
        "backend-e2e": "zcgl_e2e_test",
        "frontend-e2e": "zcgl_e2e_test",
        "import-e2e": "zcgl_import_e2e_test",
    }

    for job_name, database_name in expected_database_names.items():
        job = workflow["jobs"][job_name]
        env = job.get("env")
        services = job.get("services")

        assert isinstance(env, dict)
        assert isinstance(services, dict)
        postgres_service = services.get("postgres")
        assert isinstance(postgres_service, dict)
        postgres_env = postgres_service.get("env")
        assert isinstance(postgres_env, dict)

        expected_suffix = f"/{database_name}"
        assert str(env.get("DATABASE_URL", "")).endswith(expected_suffix)
        assert str(env.get("TEST_DATABASE_URL", "")).endswith(expected_suffix)
        if "E2E_TEST_DATABASE_URL" in env:
            assert str(env.get("E2E_TEST_DATABASE_URL", "")).endswith(expected_suffix)

        assert postgres_env.get("POSTGRES_DB") == database_name

        service_options = str(postgres_service.get("options", ""))
        assert database_name in service_options


def test_import_e2e_targets_should_only_reference_existing_backend_specs() -> None:
    repo_root = _repo_root()
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    script_text = (repo_root / "scripts" / "dev" / "run_import_e2e.sh").read_text(
        encoding="utf-8"
    )

    referenced_tests = {
        match
        for match in re.findall(r"tests/e2e/[A-Za-z0-9_./-]+\.py", makefile_text + "\n" + script_text)
    }
    missing_tests = sorted(
        str(path)
        for path in referenced_tests
        if not (repo_root / "backend" / path).exists()
    )

    assert not missing_tests, (
        "Import-focused E2E targets must not reference deleted backend specs: "
        f"{missing_tests}"
    )


def test_import_e2e_targets_should_only_reference_existing_frontend_specs() -> None:
    repo_root = _repo_root()
    makefile_text = (repo_root / "Makefile").read_text(encoding="utf-8")
    script_text = (repo_root / "scripts" / "dev" / "run_import_e2e.sh").read_text(
        encoding="utf-8"
    )

    referenced_specs = {
        match
        for match in re.findall(
            r"tests/e2e/[A-Za-z0-9_./-]+\.spec\.ts", makefile_text + "\n" + script_text
        )
    }
    missing_specs = sorted(
        str(path)
        for path in referenced_specs
        if not (repo_root / "frontend" / path).exists()
    )

    assert not missing_specs, (
        "Import-focused E2E targets must not reference deleted frontend specs: "
        f"{missing_specs}"
    )


def test_frontend_e2e_job_should_install_full_browser_matrix() -> None:
    workflow = _load_ci_workflow()
    frontend_e2e_job = workflow["jobs"]["frontend-e2e"]
    install_step = _step_by_name(frontend_e2e_job, "Install Playwright browser")
    install_script = str(install_step.get("run", ""))

    assert "playwright install --with-deps" in install_script
    assert "chromium" in install_script
    assert "firefox" in install_script
    assert "webkit" in install_script


def test_frontend_e2e_seed_should_provision_non_admin_role() -> None:
    workflow = _load_ci_workflow()
    frontend_e2e_job = workflow["jobs"]["frontend-e2e"]
    seed_step = _step_by_name(frontend_e2e_job, "Seed admin user for E2E")
    seed_script = str(seed_step.get("run", ""))

    assert "ensure_regular_role" in seed_script
    assert 'Role.name == "user"' in seed_script


def test_workflows_should_not_pin_deprecated_node20_action_majors() -> None:
    deprecated_action_versions = {
        "actions/checkout@v4",
        "actions/setup-python@v4",
        "actions/setup-node@v4",
        "actions/cache@v4",
        "actions/upload-artifact@v4",
        "actions/upload-artifact@v5",
        "codecov/codecov-action@v4",
    }
    workflow_names = ("ci.yml", "security.yml", "quality-trends.yml")

    deprecated_usage_by_workflow: dict[str, list[str]] = {}
    for workflow_name in workflow_names:
        workflow = _load_workflow(workflow_name)
        jobs = workflow.get("jobs")
        if not isinstance(jobs, dict):
            continue

        matched_uses: set[str] = set()
        for job in jobs.values():
            if not isinstance(job, dict):
                continue

            for step in _job_steps(job):
                uses = step.get("uses")
                if not isinstance(uses, str):
                    continue
                if uses in deprecated_action_versions:
                    matched_uses.add(uses)

        if matched_uses:
            deprecated_usage_by_workflow[workflow_name] = sorted(matched_uses)

    assert not deprecated_usage_by_workflow, (
        "Workflows should not pin GitHub-hosted actions that still run on deprecated Node 20 "
        f"majors: {deprecated_usage_by_workflow}"
    )
