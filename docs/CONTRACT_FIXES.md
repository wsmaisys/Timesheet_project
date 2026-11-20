# Documentation Fixes & Policy Defaults

This document records the contract defects resolved in `timesheet_openapi_django.yaml` relative to `timesheet_workforce_management_platform_specification.md` (SRS v0.9), and the baseline defaults chosen for open `TBD` items (A-01 through A-12). All policy settings are configurable at runtime by an Administrator via `GET/PATCH /api/v1/settings` (`CompanySetting`) without code changes.

---

## 1. OpenAPI 3.1.0 Contract Fixes Applied

1. **Invalid bare `responses` keys (`description:` / `content:` without status code):**
   - **Defect:** Multiple operations placed `description: Standard error response` and `content:` directly inside `responses:` rather than under a valid HTTP status key or `'default'`, causing OpenAPI 3.1 validation to fail.
   - **Fix:** Moved all default error payloads under `'default':` or `$ref: '#/components/responses/StandardError'`.
2. **Missing CSV Export endpoint (`GET /reports/time-summary/export`):**
   - **Defect:** Specified in SRS §13 and FR-RPT-003, missing from OpenAPI YAML.
   - **Fix:** Added `GET /reports/time-summary/export` returning `text/csv` with `EXPORT_TOO_LARGE` error documentation.
3. **Empty `TimesheetPatch` schema (`properties: {}`):**
   - **Defect:** `TimesheetPatch` prevented any editable timesheet metadata updates.
   - **Fix:** Added `notes` (`string | null`) and `version` (`integer`) to `TimesheetPatch`.
4. **Untyped `AuditEvent` response:**
   - **Defect:** `GET /audit-events` returned untyped `type: object` items without pagination metadata.
   - **Fix:** Added `AuditEvent` and `PagedAuditEvents` (`items`, `meta`) plus filter parameters (`entity_type`, `entity_id`, `actor_id`, `action`, `from_date`, `to_date`, `limit`, `offset`).
5. **`UserCreate.employee_code` alignment:**
   - **Defect:** SRS §8 requires `employee_code` on `User`, whereas OpenAPI `UserCreate` omitted it from `required`.
   - **Fix:** Made `employee_code` required on `User` and `UserCreate`.
6. **Consistent pagination & filters on collection endpoints:**
   - **Defect:** `GET /projects`, `GET /approvals/pending`, `GET /clients`, and `GET /assignments` lacked `limit`/`offset` pagination parameters and consistent `{items, meta}` envelopes (`PagedClients`, `PagedAssignments`).
   - **Fix:** Standardized all list endpoints on `limit`/`offset` (`default: 50`, `max: 200`) returning `{items, meta}` (`PageMeta`), matching SRS §12.
7. **Timesheet approval context & rejection visibility:**
   - **Fix:** Added `notes`, `assigned_approver_id`, `billable_minutes`, and `approval_events` (`ApprovalEvent[]`) to `Timesheet` so employees directly see rejection/reopen reasons and workflow timeline.
8. **Project budget hours:**
   - **Fix:** Added `budget_hours` (`number | null`) to `Project`, `ProjectCreate`, and `ProjectUpdate` (matching SRS §3.1).
9. **Operational & MVP completeness endpoints:**
   - Added `/auth/login`, `/auth/refresh`, `/auth/logout` for JWT session issuance and inactive-user rejection (`AUTH_ACCOUNT_DISABLED`).
   - Added `PATCH /clients/{client_id}`, `PATCH /projects/{project_id}/tasks/{task_id}`, `PATCH /assignments/{assignment_id}` for master-data maintenance and soft deactivation.
   - Added `GET/PATCH /settings` (`FR-ADM-001`), `GET /dashboard` (SRS §14), `GET /notifications` + `read`/`read-all` (SRS §15), and `GET /health/live` + `GET /health/ready` (SRS §18).

---

## 2. Baseline Defaults for SRS `TBD` Decisions (A-01 to A-12)

| Decision ID | SRS Topic | Implemented Baseline Default | Configurability |
| :--- | :--- | :--- | :--- |
| **A-01** | Deployment model | Single-company deployment | Tenant/org fields kept cleanly modular |
| **A-02** | Entry cadence & style | Weekly Monday–Sunday periods; duration-only (no clock-in/out) | `week_start_day` configurable (`0`–`6`) |
| **A-03** | Duration storage & increment | Positive integer minutes; default `15`-min increment (`max_daily_minutes = 960`) | `entry_increment_minutes` (`5, 6, 15, 30, 60`) & `max_daily_minutes` in `CompanySetting` |
| **A-04** | Primary approver | Employee's configured `manager_id` snapshotted as `assigned_approver` on submit; self-approval disabled | `allow_self_approval` boolean in `CompanySetting` |
| **A-05** | Approval granularity | Whole-week submission & whole-week approve/reject/reopen | Transactional state machine in `apps/approvals` |
| **A-06** | Project assignments | Active `ProjectAssignment` required for `work_date` unless `User.can_override_assignment=True` | Per-user `can_override_assignment` flag |
| **A-07** | Billable flag & rates | `billable` recorded on each entry (defaults to `Project.billable_default`); no rate math in MVP | `allow_billable_override` in `CompanySetting` |
| **A-08** | Leave / internal work | Modeled via internal client/projects & tasks (`Internal` SAP workstream) | Administered via Clients/Projects/Tasks |
| **A-09** | Database engine | PostgreSQL 16 in production/Docker/CI; SQLite fallback for zero-setup local dev & tests | `DATABASE_URL` env variable |
| **A-10** | Identity & auth | Django auth + JWT (`SimpleJWT`) + `OIDCIdentityAdapter` interface ready for Entra ID / SAP IAS | `integrations` / `apps.accounts.auth_backends` |
| **A-11** | SAP integration | Configurable `sap_modules` & `sap_workstreams` taxonomy in DB; read-only `SAPTimeAdapter` staging stub | `CompanySetting` + `integrations/sap` |
| **A-12** | Audit, privacy & retention | Immutable append-only `AuditEvent` & `ApprovalEvent`; soft deactivation only (no hard deletes) | Enforced at model + queryset + admin levels |
