#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_RESULTS_DIR="$ROOT_DIR/test-results/backend"
BACKEND_JUNIT_DIR="$BACKEND_RESULTS_DIR/junit"

BACKEND_VENV_DEFAULT="$BACKEND_DIR/.venv"
BACKEND_PYTHON="${BACKEND_PYTHON:-}"
E2E_ADMIN_USERNAME="${E2E_ADMIN_USERNAME:-admin}"
E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-Admin123!@#}"

export E2E_ADMIN_USERNAME
export E2E_ADMIN_PASSWORD

if [[ -z "$BACKEND_PYTHON" ]]; then
  if [[ -x "$BACKEND_VENV_DEFAULT/bin/python" ]]; then
    BACKEND_PYTHON="$BACKEND_VENV_DEFAULT/bin/python"
  elif [[ -x "$BACKEND_VENV_DEFAULT/Scripts/python.exe" ]]; then
    BACKEND_PYTHON="$BACKEND_VENV_DEFAULT/Scripts/python.exe"
  elif command -v python >/dev/null 2>&1; then
    BACKEND_PYTHON="$(command -v python)"
  elif command -v python3 >/dev/null 2>&1; then
    BACKEND_PYTHON="$(command -v python3)"
  else
    echo "[ERROR] Python interpreter not found."
    exit 2
  fi
fi

BACKEND_PID=""
BACKEND_STARTED_BY_SCRIPT="0"

cleanup() {
  if [[ "$BACKEND_STARTED_BY_SCRIPT" == "1" && -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

wait_for_backend_ready() {
  local attempt=0
  local max_attempts=60

  until curl -fsS "http://127.0.0.1:8002/docs" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [[ "$attempt" -ge "$max_attempts" ]]; then
      echo "[ERROR] Backend did not become ready in time."
      return 1
    fi
    sleep 2
  done
}

resolve_seed_database_url() {
  local resolved=""

  if [[ "$BACKEND_STARTED_BY_SCRIPT" == "1" ]]; then
    resolved="${DATABASE_URL:-${E2E_TEST_DATABASE_URL:-${TEST_DATABASE_URL:-}}}"
  else
    resolved="${DATABASE_URL:-}"
  fi

  if [[ -z "$resolved" && -f "$BACKEND_DIR/.env" ]]; then
    resolved="$(awk -F= '/^DATABASE_URL=/{print substr($0, index($0, "=") + 1)}' "$BACKEND_DIR/.env" | tail -n 1)"
  fi

  if [[ -z "$resolved" ]]; then
    resolved="${E2E_TEST_DATABASE_URL:-${TEST_DATABASE_URL:-}}"
  fi

  printf '%s' "$resolved"
}

run_backend_import_e2e() {
  mkdir -p "$BACKEND_JUNIT_DIR"
  cd "$BACKEND_DIR"

  local resolved_e2e_db_url="${E2E_TEST_DATABASE_URL:-${TEST_DATABASE_URL:-}}"
  if [[ -n "$resolved_e2e_db_url" ]]; then
    export E2E_TEST_DATABASE_URL="$resolved_e2e_db_url"
  fi

  "$BACKEND_PYTHON" -m pytest \
    tests/e2e/test_pdf_import_e2e.py \
    tests/e2e/test_property_certificate_import_e2e.py \
    -m e2e \
    --no-cov \
    -v \
    --junitxml="$BACKEND_JUNIT_DIR/junit-import-e2e.xml"
}

seed_admin_user_for_frontend_e2e() {
  local resolved_database_url
  resolved_database_url="$(resolve_seed_database_url)"
  if [[ -z "$resolved_database_url" ]]; then
    echo "[ERROR] Cannot seed admin user: DATABASE_URL is not resolved."
    return 2
  fi

  export DATABASE_URL="$resolved_database_url"

  cd "$BACKEND_DIR"
  "$BACKEND_PYTHON" - <<'PY'
import asyncio
import os

from sqlalchemy import select

from src.database import async_session_scope
from src.models.auth import User
from src.models.organization import Organization
from src.models.rbac import Permission, Role, UserRoleAssignment, role_permissions
from src.services.core.password_service import PasswordService

ADMIN_USERNAME = os.getenv("E2E_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("E2E_ADMIN_PASSWORD", "Admin123!@#")
ORG_CODE = "E2E-ORG-ROOT"


async def ensure_organization(db):
    result = await db.execute(select(Organization).where(Organization.code == ORG_CODE))
    organization = result.scalars().first()
    if organization is None:
        organization = Organization(
            name="E2E Test Organization",
            code=ORG_CODE,
            level=1,
            sort_order=0,
            type="总部",
            status="active",
            path=f"/{ORG_CODE}",
            is_deleted=False,
            created_by="local-import-e2e",
            updated_by="local-import-e2e",
        )
        db.add(organization)
        await db.commit()
        await db.refresh(organization)
    return organization


async def ensure_admin_role(db):
    result = await db.execute(select(Role).where(Role.name == "admin"))
    role = result.scalars().first()
    if role is None:
        role = Role(
            name="admin",
            display_name="管理员",
            is_system_role=True,
            is_active=True,
            created_by="local-import-e2e",
            updated_by="local-import-e2e",
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)
    return role


async def ensure_admin_permission(db):
    result = await db.execute(
        select(Permission).where(
            Permission.resource == "system",
            Permission.action == "admin",
        )
    )
    permission = result.scalars().first()
    if permission is None:
        permission = Permission(
            name="system:admin",
            display_name="系统管理员",
            description="系统管理员权限",
            resource="system",
            action="admin",
            is_system_permission=True,
            requires_approval=False,
            created_by="local-import-e2e",
            updated_by="local-import-e2e",
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
    return permission


async def ensure_role_permission(db, role_id, permission_id):
    mapping_result = await db.execute(
        select(role_permissions).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )
    )
    if mapping_result.first() is None:
        await db.execute(
            role_permissions.insert().values(
                role_id=role_id,
                permission_id=permission_id,
                created_by="local-import-e2e",
            )
        )
        await db.commit()


async def upsert_admin_user(db, organization_id):
    result = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
    user = result.scalars().first()
    password_hash = PasswordService().get_password_hash(ADMIN_PASSWORD)

    if user is None:
        user = User(
            username=ADMIN_USERNAME,
            email=f"{ADMIN_USERNAME}@example.com",
            phone="13800000111",
            full_name="Import E2E Admin",
            password_hash=password_hash,
            is_active=True,
            is_locked=False,
            failed_login_attempts=0,
            default_organization_id=organization_id,
            created_by="local-import-e2e",
            updated_by="local-import-e2e",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.password_hash = password_hash
        user.is_active = True
        user.is_locked = False
        user.failed_login_attempts = 0
        user.locked_until = None
        user.default_organization_id = organization_id
        user.updated_by = "local-import-e2e"
        await db.commit()
        await db.refresh(user)
    return user


async def ensure_user_role_assignment(db, user_id, role_id):
    result = await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.role_id == role_id,
        )
    )
    assignment = result.scalars().first()
    if assignment is None:
        assignment = UserRoleAssignment(
            user_id=user_id,
            role_id=role_id,
            assigned_by="local-import-e2e",
            is_active=True,
        )
        db.add(assignment)
    else:
        assignment.is_active = True
        assignment.assigned_by = "local-import-e2e"
    await db.commit()


async def main():
    async with async_session_scope() as db:
        organization = await ensure_organization(db)
        role = await ensure_admin_role(db)
        permission = await ensure_admin_permission(db)
        await ensure_role_permission(db, role.id, permission.id)
        user = await upsert_admin_user(db, organization.id)
        await ensure_user_role_assignment(db, user.id, role.id)


asyncio.run(main())
PY
}

start_backend_if_needed() {
  if curl -fsS "http://127.0.0.1:8002/docs" >/dev/null 2>&1; then
    echo "[INFO] Reusing existing backend at http://127.0.0.1:8002"
    return
  fi

  mkdir -p "$BACKEND_RESULTS_DIR"
  cd "$BACKEND_DIR"
  "$BACKEND_PYTHON" -m alembic upgrade head >/dev/null

  "$BACKEND_PYTHON" -m uvicorn src.main:app --host 127.0.0.1 --port 8002 \
    >"$BACKEND_RESULTS_DIR/import-e2e-backend.log" 2>&1 &
  BACKEND_PID="$!"
  BACKEND_STARTED_BY_SCRIPT="1"
  echo "$BACKEND_PID" > "$BACKEND_RESULTS_DIR/import-e2e-backend.pid"

  wait_for_backend_ready
}

run_frontend_import_e2e() {
  cd "$FRONTEND_DIR"
  pnpm e2e \
    tests/e2e/user/import-guardrails.spec.ts \
    tests/e2e/rental/import-success.spec.ts \
    tests/e2e/user/property-certificate-import-success.spec.ts \
    --project=chromium
}

echo "[1/4] Running backend import-focused E2E suite"
run_backend_import_e2e

echo "[2/4] Ensuring backend API is available for frontend import E2E suite"
start_backend_if_needed

echo "[3/4] Seeding admin user for frontend import E2E suite"
seed_admin_user_for_frontend_e2e

echo "[4/4] Running frontend import-focused E2E suite"
run_frontend_import_e2e

echo "[DONE] Import-focused E2E regression suite passed."
