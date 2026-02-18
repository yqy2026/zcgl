---
name: frontend-inspection
description: Browser-based frontend inspection for the local zcgl web app. Use when users ask to巡检前端、冒烟测试页面、检查模块是否正常、验证登录后功能可用、收集控制台报错/失败请求/截图，或需要一份结构化前端巡检报告。
---

# Frontend Inspection

## Overview

Run a repeatable frontend smoke inspection against local zcgl routes, then output a JSON report with pass/warn/fail status, screenshots, console issues, request failures, and HTTP errors.

## Workflow

1. Confirm services are running (`make dev` or existing frontend/backend processes).
2. Run `node .agents/skills/frontend-inspection/scripts/inspect_frontend.js --help` first, then execute a full or scoped inspection.
3. Read the generated `report.json` and highlight only actionable findings.
4. If issues are found, rerun with a narrowed route set and include before/after evidence.

## Commands

Run from repository root:

```bash
node .agents/skills/frontend-inspection/scripts/inspect_frontend.js --help
```

Full inspection (default route set):

```bash
node .agents/skills/frontend-inspection/scripts/inspect_frontend.js
```

Scoped inspection:

```bash
node .agents/skills/frontend-inspection/scripts/inspect_frontend.js \
  --route /dashboard \
  --route /assets/list \
  --route /system/users
```

Use a custom route file (one route per line):

```bash
node .agents/skills/frontend-inspection/scripts/inspect_frontend.js \
  --routes-file path/to/routes.txt
```

## Inputs

- Credentials default to `admin/admin123`; override via `--username` and `--password`.
- Base URL defaults to `http://127.0.0.1:5173`; override via `--base-url`.
- Chromium path defaults to `CHROMIUM_PATH` env or `/usr/bin/chromium-browser`.
- Output defaults to `output/playwright/frontend-inspection-<timestamp>/report.json`.

## Output Contract

Always report:

- Summary counts: `total`, `ok`, `warn`, `fail`
- `fail` routes first, then `warn` routes
- For each non-OK route: final path, nav/login/403 state, failed requests, HTTP >=400, console issues, screenshot path
- Ignored request failures (`ignoredFailedRequests`) should be listed separately when present
- One short recommendation per actionable issue

## References

- Route scope and expected module coverage: `references/inspection-scope.md`
