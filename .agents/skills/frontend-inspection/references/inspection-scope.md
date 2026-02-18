# Inspection Scope

Use this scope for routine frontend inspection in zcgl.

## Default Route Set

- `/dashboard`
- `/assets/list`
- `/assets/new`
- `/assets/import`
- `/assets/analytics`
- `/assets/analytics-simple`
- `/rental/contracts`
- `/rental/contracts/new`
- `/rental/contracts/pdf-import`
- `/rental/ledger`
- `/rental/statistics`
- `/property-certificates`
- `/property-certificates/import`
- `/ownership`
- `/project`
- `/profile`
- `/system/users`
- `/system/roles`
- `/system/organizations`
- `/system/dictionaries`
- `/system/templates`
- `/system/logs`
- `/system/settings`

## Status Interpretation

- `ok`: no auth redirect, no navigation error, no failed request, no HTTP>=400, no console warning/error, no obvious UI error text.
- `warn`: page is reachable but has failed request, HTTP>=400, console warning/error, or UI error hint.
- `fail`: navigation error, redirected to `/login`, or denied (`/403` / access denied view).
- `net::ERR_ABORTED` is recorded under `ignoredFailedRequests` and does not by itself trigger `warn`.

## Recommended Recheck Pattern

1. Run full set once.
2. Re-run only `warn` or `fail` routes with `--route` arguments.
3. If warnings are caused by route-switch aborts (`ERR_ABORTED`), run the single route alone for confirmation.
