#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8002/api/v1}"
PROBE_USERNAME="${PROBE_USERNAME:-manager1}"
PASSWORD="${PASSWORD:-}"
SEARCH_A="${SEARCH_A:-P3B}"
SEARCH_B="${SEARCH_B:-甲}"
WORK_DIR="${WORK_DIR:-tmp}"

if [[ -z "${PASSWORD}" ]]; then
  cat <<USAGE >&2
Usage:
  PASSWORD='<password>' scripts/dev/p3b_api_probe.sh

Optional env vars:
  BASE_URL (default: http://127.0.0.1:8002/api/v1)
  PROBE_USERNAME (default: manager1)
  SEARCH_A (default: P3B)
  SEARCH_B (default: 甲)
  WORK_DIR (default: tmp)
USAGE
  exit 2
fi

mkdir -p "${WORK_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COOKIE_FILE="${WORK_DIR}/p3b-probe-${STAMP}.cookies"
LOGIN_JSON="${WORK_DIR}/p3b-probe-login-${STAMP}.json"
CAP_JSON="${WORK_DIR}/p3b-probe-capabilities-${STAMP}.json"
SEARCH_A_JSON="${WORK_DIR}/p3b-probe-search-a-${STAMP}.json"
SEARCH_B_JSON="${WORK_DIR}/p3b-probe-search-b-${STAMP}.json"

urlencode() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import quote
print(quote(sys.argv[1]))
PY
}

SEARCH_A_ENCODED="$(urlencode "${SEARCH_A}")"
SEARCH_B_ENCODED="$(urlencode "${SEARCH_B}")"

LOGIN_CODE="$(curl --noproxy '*' -sS -o "${LOGIN_JSON}" -w '%{http_code}' \
  -X POST "${BASE_URL}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"identifier\":\"${PROBE_USERNAME}\",\"password\":\"${PASSWORD}\",\"remember\":false}" \
  -c "${COOKIE_FILE}")"

if [[ "${LOGIN_CODE}" != "200" ]]; then
  echo "[FAIL] login status=${LOGIN_CODE} response_file=${LOGIN_JSON}" >&2
  exit 1
fi

CAP_CODE="$(curl --noproxy '*' -sS -o "${CAP_JSON}" -w '%{http_code}' \
  "${BASE_URL}/auth/me/capabilities" \
  -b "${COOKIE_FILE}")"
if [[ "${CAP_CODE}" != "200" ]]; then
  echo "[FAIL] capabilities status=${CAP_CODE} response_file=${CAP_JSON}" >&2
  exit 1
fi

python3 - "${CAP_JSON}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
capabilities = payload.get("capabilities", [])
party_item = next((item for item in capabilities if item.get("resource") == "party"), None)
if party_item is None or "read" not in (party_item.get("actions") or []):
    print("[FAIL] capabilities does not include party.read", file=sys.stderr)
    sys.exit(1)

perspectives = party_item.get("perspectives") or []
scope = (party_item.get("data_scope") or {}).get("manager_party_ids") or []
print(f"[PASS] capabilities_count={len(capabilities)} party_actions={party_item.get('actions')} perspectives={perspectives} manager_scope_count={len(scope)}")
PY

SEARCH_A_CODE="$(curl --noproxy '*' -sS -o "${SEARCH_A_JSON}" -w '%{http_code}' \
  "${BASE_URL}/parties?search=${SEARCH_A_ENCODED}&limit=20" \
  -b "${COOKIE_FILE}")"
SEARCH_B_CODE="$(curl --noproxy '*' -sS -o "${SEARCH_B_JSON}" -w '%{http_code}' \
  "${BASE_URL}/parties?search=${SEARCH_B_ENCODED}&limit=20" \
  -b "${COOKIE_FILE}")"

if [[ "${SEARCH_A_CODE}" != "200" ]]; then
  echo "[FAIL] search_a status=${SEARCH_A_CODE} response_file=${SEARCH_A_JSON}" >&2
  exit 1
fi
if [[ "${SEARCH_B_CODE}" != "200" ]]; then
  echo "[FAIL] search_b status=${SEARCH_B_CODE} response_file=${SEARCH_B_JSON}" >&2
  exit 1
fi

python3 - "${SEARCH_A_JSON}" "${SEARCH_B_JSON}" <<'PY'
import json
import sys
from pathlib import Path

search_a = json.loads(Path(sys.argv[1]).read_text())
search_b = json.loads(Path(sys.argv[2]).read_text())

def summarize(items):
    codes = [item.get("code") for item in items]
    return len(items), codes

count_a, codes_a = summarize(search_a)
count_b, codes_b = summarize(search_b)
print(f"[PASS] search_a_count={count_a} search_a_codes={codes_a}")
print(f"[PASS] search_b_count={count_b} search_b_codes={codes_b}")
PY

echo "[DONE] files: ${LOGIN_JSON} ${CAP_JSON} ${SEARCH_A_JSON} ${SEARCH_B_JSON}"
