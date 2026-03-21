# CI Baseline Restoration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the current CI baseline on `develop` by fixing the broken Trivy action pin and clearing the existing backend/frontend formatting blockers without mixing business-logic changes into PR #43.

**Architecture:** Keep the perspective follow-up PR isolated. Repair the failing CI entry points in a dedicated branch: first the external workflow dependency in `.github/workflows/security.yml`, then backend `ruff format` drift for `backend/src/**`, then frontend `oxfmt` drift for `frontend/src/**/*.{ts,tsx,json,css,scss,md}`. Use generated file inventories and split them into <=20-file batches so each formatting commit stays reviewable and easy to revert.

**Tech Stack:** GitHub Actions, gh CLI, Python 3.12 + uv + Ruff, Node 20 + pnpm 10 + Oxfmt, Markdown docs.

---

## Scope And Constraints

- Fix only the three currently known CI blockers:
  - `.github/workflows/security.yml` Trivy action tag no longer resolves.
  - `backend/src/**` fails `uv run ruff format --check src`.
  - `frontend/src/**/*.{ts,tsx,json,css,scss,md}` fails `pnpm format:check`.
- Do not mix any of these changes into `pr/2026-03-17-perspective-final`.
- Do not widen backend formatting to `backend/tests/**` in this branch unless CI scope is intentionally changed in a separate reviewed step.
- Do not widen frontend formatting to `frontend/scripts/**`, `frontend/docs/**`, or repo-root docs in this branch; CI only blocks on `frontend/src/**`.
- All formatting commits must be format-only. If a batch produces semantic edits or generated file churn, stop and investigate before committing.
- Keep `CHANGELOG.md` current as each implemented batch lands.

## Root Cause Snapshot

| Surface | Evidence date | Root cause |
| --- | --- | --- |
| `Trivy Scan` | 2026-03-21 | `.github/workflows/security.yml` pins `aquasecurity/trivy-action@0.24.0`, and GitHub Actions can no longer resolve that version. |
| `Backend Lint & Type Check` | 2026-03-21 and 2026-03-13 | CI fails in `Run Ruff formatting check`; `develop` already had the same red gate before this branch. |
| `Frontend Lint & Type Check` | 2026-03-21 and 2026-03-13 | CI fails in `Run Oxfmt check`; `develop` already had the same red gate before this branch. |

## File Map

- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/.github/workflows/security.yml`
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/backend/src/**` (format-only, batched)
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/frontend/src/**` (format-only, batched)
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/CHANGELOG.md`
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/docs/plans/README.md`
- Create: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/docs/plans/2026-03-21-ci-baseline-restoration-plan.md`
- Scratch only: `/tmp/backend-ruff-files.txt`, `/tmp/backend-ruff-batch-*`, `/tmp/frontend-oxfmt-files.txt`, `/tmp/frontend-oxfmt-batch-*`

## Chunk 1: Diagnose And Unblock Workflow Setup

### Task 1: Capture the exact local blockers and batch inventories

**Files:**
- Reference: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/.github/workflows/ci.yml`
- Reference: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/.github/workflows/security.yml`
- Scratch: `/tmp/backend-ruff-files.txt`
- Scratch: `/tmp/backend-ruff-batch-*`
- Scratch: `/tmp/frontend-oxfmt-files.txt`
- Scratch: `/tmp/frontend-oxfmt-batch-*`

- [ ] **Step 1: Reproduce the backend formatting failure**

Run: `cd backend && uv run ruff format --check src`
Expected: FAIL with one or more `Would reformat:` lines under `src/`.

- [ ] **Step 2: Save the backend failing-file inventory**

Run: `cd backend && uv run ruff format --check src 2>&1 | sed -n 's/^Would reformat: //p' > /tmp/backend-ruff-files.txt`
Expected: `/tmp/backend-ruff-files.txt` is non-empty and contains only `src/...` paths.

- [ ] **Step 3: Split backend formatting work into reviewable batches**

Run: `split -l 20 /tmp/backend-ruff-files.txt /tmp/backend-ruff-batch-`
Expected: one or more `/tmp/backend-ruff-batch-*` files, each with at most 20 paths.

- [ ] **Step 4: Reproduce the frontend formatting failure**

Run: `cd frontend && pnpm format:check`
Expected: FAIL with one or more `src/...` paths reported by Oxfmt.

- [ ] **Step 5: Save the frontend failing-file inventory**

Run: `cd frontend && pnpm format:check 2>&1 | awk '/^src\\// {print $1}' > /tmp/frontend-oxfmt-files.txt`
Expected: `/tmp/frontend-oxfmt-files.txt` is non-empty and contains only `src/...` paths.

- [ ] **Step 6: Split frontend formatting work into reviewable batches**

Run: `split -l 20 /tmp/frontend-oxfmt-files.txt /tmp/frontend-oxfmt-batch-`
Expected: one or more `/tmp/frontend-oxfmt-batch-*` files, each with at most 20 paths.

- [ ] **Step 7: Commit nothing; keep these inventories as disposable execution scratch**

Run: `git status --short`
Expected: no tracked-file changes yet.

### Task 2: Repair the broken Trivy action pin

**Files:**
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/.github/workflows/security.yml`

- [ ] **Step 1: Verify the current Trivy action tag is invalid**

Run: `gh api repos/aquasecurity/trivy-action/git/ref/tags/0.24.0`
Expected: FAIL with 404 or not-found output.

- [ ] **Step 2: Discover a current published upstream tag**

Run: `gh api repos/aquasecurity/trivy-action/tags --jq '.[0:10].[].name'`
Expected: one or more currently published tags from the upstream action repo.

- [ ] **Step 3: Update the workflow to a valid published tag or the immutable commit SHA for that tag**

Edit: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/.github/workflows/security.yml`

- [ ] **Step 4: Verify the workflow diff is cleanly scoped**

Run: `git diff --check -- .github/workflows/security.yml`
Expected: PASS with no whitespace or conflict-marker issues.

- [ ] **Step 5: Commit the Trivy-only fix**

```bash
git add .github/workflows/security.yml CHANGELOG.md
git commit -m "fix(ci): restore trivy action resolution"
```

## Chunk 2: Restore Backend Ruff Format Baseline

### Task 3: Execute backend Ruff batches generated from `/tmp/backend-ruff-batch-*`

**Files:**
- Modify: paths listed in `/tmp/backend-ruff-batch-*`, restricted to `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/backend/src/**`

- [ ] **Step 1: Process the first backend batch only**

Run: `cd backend && uv run ruff format $(cat /tmp/backend-ruff-batch-aa)`
Expected: only the files listed in `/tmp/backend-ruff-batch-aa` change.

- [ ] **Step 2: Verify the first backend batch is clean**

Run: `cd backend && uv run ruff format --check $(cat /tmp/backend-ruff-batch-aa) && uv run ruff check $(cat /tmp/backend-ruff-batch-aa)`
Expected: PASS.

- [ ] **Step 3: Commit the first backend batch**

```bash
git add backend/src CHANGELOG.md
git commit -m "style(backend): format ruff batch 1"
```

- [ ] **Step 4: Repeat the same format -> verify -> commit cycle for each remaining `/tmp/backend-ruff-batch-*` file**

Run: `ls /tmp/backend-ruff-batch-*`
Expected: process each batch sequentially; do not combine batches if the combined diff exceeds 20 files.

- [ ] **Step 5: Verify the backend CI formatting gate at the end**

Run: `cd backend && uv run ruff format --check src && uv run ruff check src`
Expected: PASS.

## Chunk 3: Restore Frontend Oxfmt Baseline

### Task 4: Execute frontend Oxfmt batches generated from `/tmp/frontend-oxfmt-batch-*`

**Files:**
- Modify: paths listed in `/tmp/frontend-oxfmt-batch-*`, restricted to `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/frontend/src/**`

- [ ] **Step 1: Process the first frontend batch only**

Run: `cd frontend && pnpm exec oxfmt --config .oxfmtrc.json --write $(cat /tmp/frontend-oxfmt-batch-aa)`
Expected: only the files listed in `/tmp/frontend-oxfmt-batch-aa` change.

- [ ] **Step 2: Verify the first frontend batch is clean**

Run: `cd frontend && pnpm exec oxfmt --config .oxfmtrc.json --check $(cat /tmp/frontend-oxfmt-batch-aa)`
Expected: PASS.

- [ ] **Step 3: Commit the first frontend batch**

```bash
git add frontend/src CHANGELOG.md
git commit -m "style(frontend): format oxfmt batch 1"
```

- [ ] **Step 4: Repeat the same write -> verify -> commit cycle for each remaining `/tmp/frontend-oxfmt-batch-*` file**

Run: `ls /tmp/frontend-oxfmt-batch-*`
Expected: process each batch sequentially; do not combine batches if the combined diff exceeds 20 files.

- [ ] **Step 5: Verify the frontend CI formatting gate at the end**

Run: `cd frontend && pnpm format:check && pnpm lint && pnpm type-check && pnpm type-check:e2e && pnpm check:route-authz`
Expected: PASS.

## Chunk 4: Final Verification And Handoff

### Task 5: Re-run the branch-level verification gates and prepare a clean PR

**Files:**
- Modify: `/home/y/projects/zcgl/.worktrees/ci-baseline-restoration/CHANGELOG.md` (final wording adjustment only if the implementation details changed)

- [ ] **Step 1: Verify backend and frontend local gates together**

Run: `DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/zcgl_test" make check`
Expected: PASS if the local database/test environment is available; if not, capture the exact blocker and run the largest passing subset (`lint-backend`, `lint-frontend`, `type-check`, `docs-lint`) before pushing.

- [ ] **Step 2: Push the dedicated CI-baseline branch**

```bash
git push -u origin fix/2026-03-21-ci-baseline-restoration
```

- [ ] **Step 3: Open a dedicated PR for CI baseline restoration**

Run: `gh pr create --base develop --head fix/2026-03-21-ci-baseline-restoration`
Expected: PR created with a summary that explicitly states "format-only + workflow pin repair".

- [ ] **Step 4: Confirm the remote checks that were red are now green**

Run: `gh pr checks --watch`
Expected: `Trivy Scan`, `Backend Lint & Type Check`, and `Frontend Lint & Type Check` all PASS on this dedicated PR.

- [ ] **Step 5: Only after the dedicated CI PR is green, re-run or refresh PR #43**

Run: `gh pr checks 43 --repo yuist/zcgl`
Expected: the previously blocked perspective PR is no longer held red by the same baseline issues.
