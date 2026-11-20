# Timesheet & Workforce Management Platform

**Detailed Product & Software Requirements Specification**  
*For an SAP consulting firm | Baseline specification for stakeholder validation*  
**Version 0.9** • **20 November 2026** • **Status:** Draft — not yet client-approved

---

## Document control

| Attribute | Value |
| :--- | :--- |
| **Purpose** | Buildable baseline specification for a simple, role-based timesheet platform. |
| **Audience** | Client sponsor, PMO, HR, Finance, IT/SAP, product owner, designers, developers, QA. |
| **Normative status** | Requirements marked TBD require client decision. Recommendations are not approved policy. |
| **Reference style** | Structured similarly to the supplied EMP project specification and OpenAPI example. |
| **Companion contract** | `openapi.yaml` (OpenAPI 3.1.0). |

### Important implementation boundary
The client has requested a simplistic first version. This document deliberately separates the essential MVP from later workforce-management capabilities. It is detailed enough to guide implementation, but company-specific policies, integrations, user counts, hosting, retention, and legal requirements remain TBD until confirmed. Do not silently convert assumptions into production rules.

---

## 1. Executive summary
The platform is a web application through which employees record time spent on assigned client and internal projects; managers review and approve submitted timesheets; and authorised administrators maintain users, projects, tasks, assignments, working calendars and configuration. The initial product is a time-recording and approval system, not a full HRMS, payroll engine, attendance surveillance product, ERP replacement or project-planning suite.

---

## 2. Goals and success measures
* Provide one authoritative location for employee time entries and approval history.
* Reduce spreadsheet/email-based collection and manual consolidation.
* Give employees a quick weekly workflow to record, save and submit time.
* Give managers a controlled queue to approve or return timesheets with reasons.
* Give authorised management basic visibility into submitted hours by employee, project, date range and billable classification.
* Preserve traceability of changes, approvals and administrative actions.

| Measure | Proposed acceptance measure | Owner / target |
| :--- | :--- | :--- |
| **Submission coverage** | At least 95% of expected timesheets submitted by configured deadline | TBD |
| **Approval turnaround** | Median time from submission to decision | TBD |
| **Entry usability** | Typical employee completes a weekly timesheet in under 5 minutes once assignments are configured | Proposed |
| **Data integrity** | No duplicate entry IDs; totals reconcile to entry minutes | Mandatory |
| **Auditability** | Every submit, approve, reject, reopen and privileged edit has actor and timestamp | Mandatory |

---

## 3. Scope

### 3.1 MVP — included
* Authentication and user account lifecycle (prefer company SSO if confirmed; local auth fallback is a deployment decision).
* Roles and permission checks: Employee, Manager/Approver, Administrator; optional read-only Management role.
* Employee profile basics: name, email, employee code, department, manager, location/time zone, active status.
* Client and project register; project code, name, client, dates, status, project manager, billable default and optional budget hours.
* Project task/work-item list with code, name, active status and optional SAP workstream/module classification.
* Employee-to-project assignments with effective dates and optional allocation percentage.
* Weekly timesheet with date, project, task, duration in minutes, billable flag and work description.
* Draft save, edit, submit, approve, reject/return, resubmit and authorised reopen.
* Employee, approver and admin dashboards; basic filters and CSV export.
* In-app/email notification events (delivery provider TBD).
* Audit log for material changes and workflow events.
* Configurable working week, expected daily minutes, submission deadline, entry increment and time zone.

### 3.2 Explicitly out of MVP unless approved
* Clock-in/clock-out, GPS tracking, screenshots, keystroke monitoring or employee surveillance.
* Payroll calculation, payslip generation, leave accrual engine, attendance device integration.
* Invoice generation, revenue recognition, full project financial accounting or SAP financial posting.
* Automatic SAP master-data synchronisation; AI-generated entries or productivity scoring.
* Complex multi-stage workflow designer, mobile native app, client portal, resource forecasting and predictive analytics.

### 3.3 Future-ready but not MVP
Keep stable identifiers, audit events, structured categories, API versioning, tenant/company boundary if multi-entity use is confirmed, integration adapters, and a permission-aware reporting layer. AI must call authorised application services; it must not write directly to production tables.

---

## 4. Assumptions and decisions requiring confirmation

| ID | Baseline assumption / recommendation | Client decision required |
| :--- | :--- | :--- |
| **A-01** | Single company deployment; multi-tenant SaaS is not assumed. | Single legal entity or multiple entities/business units? |
| **A-02** | Weekly timesheet, duration-based entries, no clock-in/out. | Weekly or daily? Duration or attendance clock? |
| **A-03** | Time stored as integer minutes; display format configurable. | Allowed increment: 5/6/15/30/60 minutes? |
| **A-04** | One primary approver per employee for MVP. | Line manager, project manager, or both? |
| **A-05** | Timesheet submitted as a whole week; approve/reject whole timesheet. | Need line-level or multi-project approval? |
| **A-06** | Employees can enter time only on active assigned projects and tasks. | Allow unassigned project time or admin overrides? |
| **A-07** | Billable flag is recorded; no billing rate calculation in MVP. | Need billing rates/cost rates in first release? |
| **A-08** | Leave is represented as an activity category or non-project entry; no leave balance engine. | Separate leave module required? |
| **A-09** | PostgreSQL recommended for production. | Existing company database/cloud standards? |
| **A-10** | SSO preferred; exact identity provider TBD. | Microsoft Entra ID, SAP IAS, other? |
| **A-11** | SAP integration is not assumed for MVP. | Which SAP product, modules, interface and system of record? |
| **A-12** | Retention, residency and compliance policy TBD. | Countries, GDPR/local laws, retention schedule? |

---

## 5. Actors, roles and permissions

| Role | Purpose | Core permissions |
| :--- | :--- | :--- |
| **Employee** | Records own time. | View own profile/assignments; create/edit own draft; submit; view own status/history; edit returned timesheet. |
| **Manager / Approver** | Reviews assigned employees. | View direct reports or explicitly assigned approval scope; approve; reject with reason; request correction; view team reports. |
| **Administrator** | Maintains platform configuration and master data. | Manage users, roles, clients, projects, tasks, assignments, calendars and settings; reopen timesheets with reason; view audit. |
| **Management Viewer** | Read-only business oversight; optional. | View aggregated dashboards/reports within granted organisational scope; export if permitted. |

RBAC must be enforced on the server for every endpoint. UI hiding is not security. Scope checks must also verify company/department/project/manager relationships. Deny by default. A user cannot grant themselves roles or expand their own data scope.

---

## 6. Core workflows

### 6.1 Employee weekly timesheet
1. Employee signs in and opens **My Timesheet** for a week (Monday–Sunday default; week start configurable).
2. System loads active assignments, tasks, calendar and existing draft/returned entries.
3. Employee adds one or more rows. Each row contains work date, project, task, duration, billable classification and description.
4. Employee saves draft. Draft can be changed until submitted.
5. System validates required fields, active assignment/date range, duration increment, duplicate/overlap policy and configured daily/weekly limits.
6. Employee submits the week. System records submitter and timestamp, changes status to **Submitted** and creates an approval task.
7. Assigned approver receives a notification and reviews totals and line items.
8. Approver approves or rejects/returns with a mandatory reason on rejection.
9. Approved timesheet becomes locked. Returned timesheet becomes editable by employee and must be resubmitted.
10. Any exceptional reopen requires authorised permission, reason, actor and audit event.

### 6.2 Status model

| Status | Meaning | Allowed next states |
| :--- | :--- | :--- |
| **Draft** | Employee is preparing entries. | Submitted |
| **Submitted** | Awaiting approver decision; employee edits blocked. | Approved, Rejected |
| **Rejected** | Returned to employee with reason; editable. | Submitted |
| **Approved** | Finalised and locked. | Reopened only by authorised admin/manager action |
| **Reopened** | Previously approved/submitted period reopened with reason. | Submitted |
| **Cancelled** | Administrative terminal state if configured; history retained. | None |

Do not delete approved or submitted timesheets as ordinary CRUD. Use controlled correction/reopen flows with audit. Status changes must be transactional.

### 6.3 Approval rules
* Approver is resolved from employee's configured manager/approval assignment at submission time; snapshot approver identity on the approval record.
* Approver cannot approve their own timesheet unless an explicit delegated policy permits it.
* Approval/rejection requires the timesheet to be **Submitted** and approver to have scope.
* Reject action requires a non-empty reason (recommended 10–1,000 characters).
* Duplicate approval actions are idempotently rejected or return current state; no duplicate approval events.
* Delegation and escalation are future scope unless confirmed.

---

## 7. Functional requirements

| ID | Requirement | Priority |
| :--- | :--- | :--- |
| **FR-AUTH-001** | User shall authenticate using the configured identity provider. | MUST |
| **FR-AUTH-002** | Unauthenticated requests shall receive 401; authenticated but unauthorised requests 403. | MUST |
| **FR-USER-001** | Administrator shall create, update, deactivate and list user profiles. | MUST |
| **FR-USER-002** | Deactivated users shall not sign in or create new entries; historical records remain. | MUST |
| **FR-PROJ-001** | Administrator shall create and maintain clients and projects with unique project code. | MUST |
| **FR-PROJ-002** | Project status shall be Draft, Active, On Hold or Closed. | MUST |
| **FR-PROJ-003** | Project shall have effective start/end dates; end must not precede start. | MUST |
| **FR-TASK-001** | Administrator/authorised PM shall maintain project tasks and optional SAP workstream/module tags. | MUST |
| **FR-ASG-001** | Authorised user shall assign an employee to a project for a date range. | MUST |
| **FR-ASG-002** | Employee may enter time only where assignment is active for the work date, unless override permission is granted. | MUST |
| **FR-TS-001** | Employee shall create and edit own Draft timesheet entries. | MUST |
| **FR-TS-002** | Entry duration shall be stored as positive integer minutes. | MUST |
| **FR-TS-003** | Entry shall reference a valid project and task; task must belong to project. | MUST |
| **FR-TS-004** | Entry shall include work date, duration, billable flag and description; description required by default. | MUST |
| **FR-TS-005** | System shall calculate daily and weekly totals from entries, never accept client-supplied totals as authoritative. | MUST |
| **FR-TS-006** | Employee shall submit a timesheet period for approval. | MUST |
| **FR-TS-007** | Submitted/Approved entries shall be immutable to employee. | MUST |
| **FR-TS-008** | Returned entries shall be editable and resubmittable. | MUST |
| **FR-APP-001** | Approver shall list pending timesheets within their scope. | MUST |
| **FR-APP-002** | Approver shall approve or reject with reason; decision shall be audited. | MUST |
| **FR-APP-003** | Approved timesheet shall be locked against ordinary edits. | MUST |
| **FR-APP-004** | Authorised user shall reopen with mandatory reason. | SHOULD |
| **FR-RPT-001** | Authorised users shall view time totals by date range, employee, project and billable status. | MUST |
| **FR-RPT-002** | Reports shall respect the same row-level access rules as APIs. | MUST |
| **FR-RPT-003** | Authorised users shall export filtered report data to CSV. | SHOULD |
| **FR-NOT-001** | System shall notify employee on rejection and approver on submission. | SHOULD |
| **FR-AUD-001** | System shall record actor, action, entity, entity ID, timestamp and relevant before/after values for material changes. | MUST |
| **FR-ADM-001** | Administrator shall configure week start, timezone, work schedule, entry increment and submission deadline. | MUST |

---

## 8. Field definitions and validation

| Object / field | Type / format | Rules |
| :--- | :--- | :--- |
| `User.employee_code` | string | Required; unique within company; trim whitespace. |
| `User.email` | email string | Required; normalise lowercase; unique; validated format. |
| `Project.project_code` | string | Required; unique; immutable after use unless admin migration. |
| `Project.status` | enum | `Draft`, `Active`, `OnHold`, `Closed`. |
| `Project.start_date` / `end_date` | date ISO 8601 | `start <= end`; nullable end only if open-ended policy allows. |
| `Task.task_code` / `name` | string | Required; task belongs to exactly one project in MVP. |
| `Assignment.start_date` / `end_date` | date | Employee/project active; `start <= end`; overlapping assignments allowed only if policy permits. |
| `TimeEntry.work_date` | date `YYYY-MM-DD` | Must be within timesheet period and assignment effective dates. |
| `TimeEntry.duration_minutes` | integer | Positive; `<=` configured daily maximum; multiple of configured increment. |
| `TimeEntry.description` | string | Required; trim; 1–1,000 characters recommended; reject whitespace-only. |
| `TimeEntry.billable` | boolean | Required; default from project but employee may change only if policy permits. |
| `Timesheet.period_start` / `end` | date | Canonical week boundary; `end >= start`; must match configured period. |
| `Approval.reason` | string | Required for rejection/reopen; 1–1,000 characters after trim. |

---

## 9. Business rules
* **BR-001:** All durations are stored as integer minutes. UI may display decimal hours or `HH:MM`; conversions must be exact.
* **BR-002:** A timesheet period is unique per employee and period start. Enforce a database unique constraint.
* **BR-003:** An entry's `work_date` must fall inside its parent timesheet period.
* **BR-004:** Entry duration must be positive and comply with configured increment.
* **BR-005:** Entry project and task must be active and assignment valid on `work_date`, except authorised override.
* **BR-006:** Daily and weekly totals are derived from entries. Configured expected hours produce warnings or blockers according to policy.
* **BR-007:** The platform must not assume every employee works 8 hours/day or 40 hours/week; use configurable schedules and calendars.
* **BR-008:** No overlapping clock intervals exist in duration-only MVP. If interval-based entry is later introduced, overlap checks become mandatory.
* **BR-009:** Submitted and approved records cannot be changed by employee. Approved changes require reopen/correction workflow.
* **BR-010:** Approval action must verify current status and permission in one database transaction.
* **BR-011:** Project closure prevents new entries after closure date; historical entries remain readable. Exact policy TBD.
* **BR-012:** Time zone is stored/handled consistently; `work_date` is a local calendar date in employee's configured timezone; event timestamps are UTC.
* **BR-013:** Deactivation never cascades deletion of historical timesheets, approvals or audit events.
* **BR-014:** CSV export must apply filters and permission scope; exports must not leak hidden employees/projects.
* **BR-015:** Every mutation should support request correlation ID; create/submit operations should support idempotency where retries could duplicate effects.

---

## 10. Error handling contract
All API errors use a consistent JSON envelope. HTTP status is authoritative; application `error_code` is stable and machine-readable.

```json
{
  "error": {
    "code": "TS_ENTRY_INVALID_DURATION",
    "message": "Duration must be a positive multiple of 15 minutes.",
    "details": [
      {
        "field": "duration_minutes",
        "issue": "not_multiple_of_increment"
      }
    ],
    "request_id": "..."
  }
}
```

### HTTP Status Codes

| HTTP | When | Client behaviour |
| :--- | :--- | :--- |
| **400** | Malformed JSON, invalid field, business rule validation. | Show field-level message; do not retry unchanged request. |
| **401** | Missing/invalid/expired authentication. | Re-authenticate. |
| **403** | Authenticated but role/scope insufficient. | Show access denied; do not reveal protected resource details. |
| **404** | Resource does not exist or is outside visible scope. | Show not found. |
| **409** | State conflict, duplicate period, already submitted/approved, stale update. | Refresh current state; ask user to resolve conflict. |
| **422** | Well-formed request cannot be processed due to semantic validation (optional convention). | Show field/business errors. |
| **429** | Rate limit exceeded. | Retry after `Retry-After`. |
| **500** | Unexpected server error. | Show generic message and request ID; log details server-side. |
| **503** | Temporary dependency/service unavailable. | Retry with backoff where safe. |

### Application Error Codes

| Error code | Trigger |
| :--- | :--- |
| `AUTH_INVALID_CREDENTIALS` | Login rejected. |
| `AUTH_ACCOUNT_DISABLED` | Account is inactive. |
| `AUTH_FORBIDDEN` | Permission or scope denied. |
| `USER_EMAIL_EXISTS` | Email already registered. |
| `PROJECT_CODE_EXISTS` | Project code already exists. |
| `PROJECT_INACTIVE` | Project cannot accept new entries. |
| `TASK_NOT_IN_PROJECT` | Task does not belong to selected project. |
| `ASSIGNMENT_NOT_ACTIVE` | Employee is not assigned on work date. |
| `TS_PERIOD_EXISTS` | Employee already has a timesheet for period. |
| `TS_PERIOD_INVALID` | Period boundaries invalid. |
| `TS_NOT_EDITABLE` | Timesheet state does not allow edits. |
| `TS_ENTRY_INVALID_DURATION` | Duration invalid or violates increment. |
| `TS_ENTRY_DATE_OUTSIDE_PERIOD` | Entry date outside period. |
| `TS_ENTRY_DUPLICATE` | Duplicate entry detected under configured duplicate policy. |
| `TS_SUBMISSION_INCOMPLETE` | Required fields or configured hours are missing. |
| `TS_ALREADY_SUBMITTED` | Timesheet is not in Draft/Rejected state. |
| `APPROVER_OUT_OF_SCOPE` | Approver cannot act on this timesheet. |
| `APPROVAL_REASON_REQUIRED` | Rejection/reopen reason missing. |
| `TS_STATE_CONFLICT` | Timesheet state changed since it was loaded. |
| `EXPORT_TOO_LARGE` | Export exceeds configured limit. |
| `RATE_LIMIT_EXCEEDED` | API request limit exceeded. |
| `INTERNAL_ERROR` | Unexpected error; include `request_id` in support request. |

---

## 11. Data model

| Entity | Key attributes | Relationships / notes |
| :--- | :--- | :--- |
| **User** | `id`, `employee_code`, `email`, `full_name`, `role`/`status`, `manager_id`, `department`, `timezone` | Manager self-reference; historical actor references retained. |
| **Client** | `id`, `code`, `name`, `status` | One client has many projects; internal client record may represent internal work. |
| **Project** | `id`, `client_id`, `code`, `name`, `dates`, `status`, `project_manager_id`, `billable_default` | Has tasks, assignments and time entries. |
| **Task** | `id`, `project_id`, `code`, `name`, `status`, `sap_workstream`, `sap_module` | Belongs to one project in MVP. |
| **ProjectAssignment** | `id`, `user_id`, `project_id`, `start_date`, `end_date`, `allocation_percent` | Many-to-many user/project with effective dates. |
| **Timesheet** | `id`, `user_id`, `period_start`, `period_end`, `status`, `submitted_at`, `approved_at`, `version` | One per user/week; contains entries and approval events. |
| **TimeEntry** | `id`, `timesheet_id`, `project_id`, `task_id`, `work_date`, `duration_minutes`, `billable`, `description` | Duration in minutes; no hard delete after submission. |
| **ApprovalEvent** | `id`, `timesheet_id`, `actor_id`, `action`, `reason`, `created_at` | Append-only workflow history. |
| **AuditEvent** | `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `before_json`, `after_json`, `request_id`, `created_at` | Append-only; access restricted. |
| **Notification** | `id`, `user_id`, `type`, `payload`, `read_at`, `delivery_status` | In-app; email delivery optional. |
| **CompanySetting** | `key`, `value`, `updated_by`, `updated_at` | Versioned/configuration audited. |

**Recommended database constraints:** unique `lower(email)`; unique `employee_code`; unique `project_code`; `unique(user_id, period_start)`; foreign keys; check `duration_minutes > 0`; check `allocation_percent` between 0 and 100; check project/task status enums; indexes on `timesheet(user_id, period_start, status)`, `time_entry(project_id, work_date)`, `assignment(user_id, project_id, start_date, end_date)`, `approval_event(timesheet_id, created_at)`. Use soft deactivation for master data.

---

## 12. API conventions
* **Base path:** `/api/v1`. JSON request/response. UTF-8.
* IDs are opaque UUID strings in this baseline. If client requires integer IDs, decide before implementation and change contract consistently.
* Dates use `YYYY-MM-DD`. Timestamps use RFC 3339 UTC, e.g. `2026-11-20T12:30:00Z`.
* **Pagination:** `limit` (default 50, max 200), `offset`; response includes `items` and `total`. Cursor pagination may replace offset at scale.
* Filtering and sorting are allowlisted; never interpolate raw sort fields into SQL.
* `PATCH` updates supplied fields only; omitted fields remain unchanged; `null` clears only nullable fields.
* Use `ETag`/`If-Match` or `version` field for optimistic concurrency on mutable timesheets/projects.
* **Authentication:** bearer token in `Authorization` header; actual OAuth/OIDC issuer and scopes TBD.
* Never trust `user_id`, `role`, `totals`, `approval status` or `billable` authority supplied by client without server-side validation.

---

## 13. Endpoint catalogue

| Method / path | Purpose | Access |
| :--- | :--- | :--- |
| `GET /auth/me` | Current user and effective permissions | Authenticated |
| `GET/POST /users` | List/create users | Admin |
| `GET/PATCH /users/{user_id}` | Read/update user | Self limited; Admin |
| `GET/POST /clients` | List/create clients | Authenticated read / Admin write |
| `GET/POST /projects` | List/create projects | Scope read / Admin write |
| `GET/PATCH /projects/{project_id}` | Project detail/update | Scope read / Admin write |
| `GET/POST /projects/{project_id}/tasks` | List/create tasks | Project scope / Admin or PM write |
| `GET/POST /assignments` | List/create assignments | Admin/PM |
| `GET /timesheets` | List own or permitted team timesheets | Scoped |
| `POST /timesheets` | Create period timesheet | Employee own |
| `GET/PATCH /timesheets/{id}` | Read/update draft or returned timesheet | Owner or approver read |
| `POST /timesheets/{id}/entries` | Add entry | Owner, editable state |
| `PATCH/DELETE /timesheets/{id}/entries/{entry_id}` | Update/remove entry | Owner, editable state |
| `POST /timesheets/{id}/submit` | Submit period | Owner |
| `GET /approvals/pending` | Pending approval queue | Approver |
| `POST /timesheets/{id}/approve` | Approve submitted period | Assigned approver |
| `POST /timesheets/{id}/reject` | Return with reason | Assigned approver |
| `POST /timesheets/{id}/reopen` | Reopen with reason | Admin/authorised manager |
| `GET /reports/time-summary` | Aggregated hours report | Management/PM/Finance scope |
| `GET /reports/time-summary/export` | CSV export | Report permission |
| `GET /audit-events` | Audit search | Admin/auditor |

---

## 14. Dashboard requirements

| Dashboard | Widgets / data |
| :--- | :--- |
| **Employee** | Current week total; expected hours; draft/submitted/approved status; assigned projects; returned timesheet notice; recent weeks. |
| **Manager** | Pending approvals; overdue submissions; team submitted percentage; team hours by project; returned items. |
| **Administrator** | Active users/projects; projects ending soon; submission status; user/project administration shortcuts. |
| **Management viewer (optional)** | Hours by project/client/department; billable vs non-billable totals; period trends; export. |

Every metric must define its formula, date basis, timezone, included statuses, filters and permission scope before being presented as a KPI. Do not label logged hours as productivity without an agreed definition.

---

## 15. Notifications

| Event | Recipient | Content |
| :--- | :--- | :--- |
| **Timesheet submitted** | Approver | Employee, period, total hours, link to review. |
| **Timesheet approved** | Employee | Period, approver, decision timestamp. |
| **Timesheet rejected** | Employee | Period, mandatory reason, link to edit. |
| **Submission deadline approaching** | Employee | Period and configured deadline. |
| **Overdue timesheet** | Employee; optionally manager | Missing period and action. |
| **Assignment created/changed** | Employee | Project, dates, tasks and manager. |

Notification delivery failure must not roll back a saved timesheet or approval. Persist notification intent/outbox event and retry asynchronously. Avoid including sensitive descriptions in email unless client approves.

---

## 16. SAP-specific considerations
* SAP is a consulting domain, not proof that the company uses a particular SAP product internally. Model optional classifications without hardcoding one SAP landscape.
* Optional project/task attributes: SAP solution/product, module or functional area (FI, CO, MM, SD, PP, HCM, SuccessFactors, ABAP, Basis, BTP, Analytics, S/4HANA migration), workstream, phase, environment and client work package.
* Keep taxonomy configurable; values must be administered, not embedded in source code.
* Potential future integrations include SAP S/4HANA project/WBS, SAP CATS, SuccessFactors, SAP BTP, SAP Identity Authentication Services or SAP Analytics Cloud. Validate product/version, APIs, licensing, master-data owner and direction of data flow before design.
* Define a system of record for employee, client, project, task, cost centre, billing rate and approval status.
* Use integration adapter/service accounts, least privilege, retry queues, idempotency keys, reconciliation reports and dead-letter handling.
* Do not post time to SAP or payroll automatically in MVP unless expressly approved.

---

## 17. Security, privacy and audit
* TLS in transit; encryption at rest using hosting/database capabilities.
* OIDC/OAuth2 SSO preferred; MFA policy inherited from identity provider where possible.
* RBAC plus row-level scope checks; deny-by-default.
* Secure password hashing only if local passwords are enabled; never store plaintext secrets.
* Secrets in managed secret store; rotate integration credentials.
* Input validation, parameterised SQL, output encoding, CSRF protection for cookie sessions, rate limits and secure headers.
* Audit privileged actions and workflow state changes; restrict audit access; protect logs from tampering.
* Backups encrypted and restore-tested; RPO/RTO TBD.
* Data minimisation, retention/deletion policy, data subject handling and residency must be reviewed for applicable jurisdictions.
* Define whether employee work descriptions are personal data and who may view them.
* Do not implement covert monitoring, location tracking or automated punitive productivity scoring as part of this timesheet MVP.

---

## 18. Non-functional requirements

| Area | Baseline requirement / target to validate |
| :--- | :--- |
| **Performance** | 95th percentile normal API response < 2 seconds under agreed load; report/export jobs may be asynchronous. |
| **Availability** | Target uptime and maintenance windows TBD; propose 99.5% monthly for initial production. |
| **Scale** | Load test against confirmed active users, concurrency and entry volume; user count TBD. |
| **Reliability** | Transactional submit/approve; no lost committed entries; idempotent retry where relevant. |
| **Accessibility** | Target WCAG 2.2 AA for core workflows. |
| **Compatibility** | Current and previous major versions of Chrome, Edge, Firefox and Safari; confirm client devices. |
| **Observability** | Structured logs, metrics, tracing/correlation IDs, alerting and health endpoints. |
| **Recovery** | RPO/RTO, backup frequency and retention TBD. |
| **Maintainability** | Versioned API, migrations, automated tests, documented configuration and deployment. |

---

## 19. Recommended architecture
**Recommendation:** begin with a modular monolith, not microservices. It is simpler to build, deploy and operate for an initial internal platform while preserving module boundaries.

| Layer | Recommendation |
| :--- | :--- |
| **Web UI** | Responsive web client; employee, approver and admin workspaces. |
| **API** | Versioned REST API; business validation and authorization server-side. |
| **Domain modules** | Identity/access, organisation, projects, assignments, timesheets, approvals, reporting, notifications, audit. |
| **Database** | PostgreSQL recommended; relational integrity and transactions. |
| **Background worker** | Email delivery, scheduled reminders, exports and future integrations. |
| **Integration boundary** | Adapters for SAP/HR/identity/reporting systems; asynchronous where appropriate. |
| **AI boundary (future)** | Separate orchestration service using scoped APIs and audited user-confirmed actions. |

The client has explicitly identified **Django** as the required backend framework. The implementation must therefore use Python and Django. Django REST Framework (DRF) is the proposed API layer for implementing the REST contract. PostgreSQL, `drf-spectacular`, Celery/Redis and the authentication approach below are technical recommendations and remain subject to client/architecture approval.

### 19.1 Mandatory backend framework and proposed implementation stack
* **Mandatory:** Python with Django. The backend must be implemented as a Django application; the framework choice is a client requirement, not an optional recommendation.
* **Proposed API layer:** Django REST Framework (DRF), providing serializers, request validation, viewsets/API views, authentication integration, permission classes and pagination.
* **Proposed API schema tooling:** `drf-spectacular` (or another client-approved DRF-compatible OpenAPI generator). The published API contract must remain aligned with the supplied OpenAPI 3.1 document. Schema generation must be included in CI so contract drift is detected.
* **Proposed database:** PostgreSQL. Confirm the supported version, hosting model, backup policy and high-availability requirements with the client.
* **Authentication:** use Django's authentication facilities with a suitable enterprise SSO/OIDC or SAML integration if required. JWT may be used for API access where appropriate. The identity provider, token lifetime, MFA policy and session strategy remain TBD.
* **Authorization:** implement role-based and object-level access checks using DRF permission classes and Django services/querysets. Enforce tenant, department, manager and project scope on the server for every relevant operation. Never rely on frontend visibility controls.
* **Background work:** Celery with Redis is a proposed option for scheduled reminders, exports and integration jobs. It is not mandatory for the first release if synchronous processing is sufficient.
* **Administration:** Django Admin may be used for restricted internal administration of reference data and support tasks. It must use the same authorization, audit and operational controls; it is not a substitute for the employee/manager product interface.
* **Architecture:** use a modular Django monolith for the MVP. Keep domain logic in service/domain modules rather than embedding workflows in views, serializers or Django Admin hooks.

#### Suggested Django project layout
* `config/` (settings, root URLs, ASGI/WSGI)
* `apps/accounts`
* `apps/clients`
* `apps/projects`
* `apps/assignments`
* `apps/timesheets`
* `apps/approvals`
* `apps/reports`
* `apps/notifications`
* `apps/audit`
* `integrations/sap`
* `integrations/ai`
* `common/` (permissions, exceptions, pagination and shared utilities)

Names may be adjusted to the delivery team's conventions while preserving clear domain ownership.

Each Django app should own its relevant models, migrations, serializers, API views/routes, permissions and tests. Cross-domain business workflows should be coordinated through explicit service-layer functions. Use database transactions and constraints for critical state changes such as submission, approval and reopening.

* **Deployment:** package the Django application for the client-approved hosting platform. Use environment-based settings and secrets management; separate development, test/staging and production configurations; run migrations as a controlled release step; and configure structured logging, health checks, TLS, static/media handling and database backups.
* **Future AI and SAP capabilities:** keep integrations behind explicit adapter/service boundaries. Do not couple core timesheet approval or payroll-relevant rules to a particular AI model or SAP product. SAP system/version, integration method and data ownership must be confirmed before designing production connectors.

---

## 20. Testing and acceptance criteria
* Unit tests for all business rules and validation functions.
* Integration tests for database constraints, auth, permission boundaries, workflow transitions and notification outbox.
* API contract tests against OpenAPI.
* End-to-end tests: create assignment $\rightarrow$ enter week $\rightarrow$ submit $\rightarrow$ approve; reject $\rightarrow$ edit $\rightarrow$ resubmit; reopen $\rightarrow$ correct $\rightarrow$ resubmit.
* Negative tests: unassigned project, inactive task, duplicate period, invalid increment, out-of-period date, unauthorized team access, self-approval, edit approved entry.
* Concurrency test: two approvers act simultaneously; only one valid state transition succeeds.
* Security tests: IDOR, privilege escalation, injection, CSRF/session, export leakage.
* Backup restore and audit verification before production.

| Acceptance ID | Given / When | Then |
| :--- | :--- | :--- |
| **AC-01** | Employee has active assignment and creates valid entry. | Entry saves with integer minutes and correct project/task. |
| **AC-02** | Employee submits a valid period. | Status becomes Submitted; timestamp and approval task are created exactly once. |
| **AC-03** | Approver in scope approves Submitted timesheet. | Status becomes Approved; employee can no longer edit. |
| **AC-04** | Approver rejects without reason. | Request fails with `APPROVAL_REASON_REQUIRED`; no state change. |
| **AC-05** | Employee attempts to edit Approved timesheet. | Request fails with `TS_NOT_EDITABLE`. |
| **AC-06** | User requests another employee's timesheet outside scope. | API returns 403 or non-disclosing 404 consistently. |
| **AC-07** | Entry date is outside parent period. | API rejects with `TS_ENTRY_DATE_OUTSIDE_PERIOD`. |
| **AC-08** | Duration is not a multiple of configured increment. | API rejects with `TS_ENTRY_INVALID_DURATION`. |
| **AC-09** | Admin reopens approved timesheet with reason. | New state and immutable audit event are recorded. |
| **AC-10** | Report user lacks access to a department. | Department rows are not returned or exported. |

* Django model and migration tests, including database constraints and transaction rollback behaviour.
* DRF serializer and API permission tests for role-based access, object-level access and cross-project/department data isolation.
* OpenAPI schema generation and validation in CI; compare the generated contract with the published OpenAPI 3.1 contract and review intentional differences.
* Production configuration checks: `DEBUG` disabled, secrets externalised, secure cookies/headers, TLS termination and allowed-host configuration.

---

## 21. Delivery plan

| Phase | Deliverable | Exit criteria |
| :--- | :--- | :--- |
| **0. Discovery & validation** | Approved BRD/FRS, process maps, role matrix, policies, integrations inventory | Sponsor and process owners sign off; TBDs assigned. |
| **1. Foundation** | Auth, user/role, organisation, client/project/task, assignments | Admin can configure valid master data; access tests pass. |
| **2. Timesheet MVP** | Weekly timesheet, entries, draft/save, validation, submit | Employee workflow passes acceptance tests. |
| **3. Approvals & reporting** | Approval queue, approve/reject/reopen, dashboards, CSV | Workflow and report permissions pass tests. |
| **4. Pilot & production** | UAT, training, migration (if any), security review, deployment | Business sign-off, backup/restore, support runbook. |
| **5. Enhancements** | SAP integration, leave, resource planning, advanced analytics, AI | Separate business case and approved scope. |

---

## 22. Risks and dependencies

| Risk / dependency | Mitigation / required decision |
| :--- | :--- |
| **Unclear approval ownership** | Sponsor nominates process owner and approver hierarchy. |
| **Conflicting timesheet policies** | HR/PMO/Finance workshop; record policy by employee group/project. |
| **Unknown SAP landscape** | IT confirms product/version, system owner, APIs and integration scope. |
| **Overloaded MVP** | Enforce explicit in/out scope; defer payroll, leave engine and AI. |
| **Sensitive employee data** | Privacy/security review, access matrix and retention schedule. |
| **Poor master data** | Identify authoritative employee/project sources and clean-up owner. |
| **Unbounded reporting expectations** | Define metric formulas, filters, roles and export volumes. |
| **No agreed expected hours** | Configure schedules/calendars; do not hardcode 8/40-hour assumptions. |

---

## 23. Client decisions required before build
1. Confirm number of employees, expected growth and concurrent users.
2. Confirm countries, legal entities, locations, time zones and work calendars.
3. Confirm weekly vs daily entry and whether clock-in/clock-out is required.
4. Confirm time increments, expected hours, overtime and deadline policy.
5. Confirm approver resolution and whether project managers also approve.
6. Confirm project/task hierarchy and required SAP taxonomy.
7. Confirm billable/non-billable rules and whether rates/costs are in MVP.
8. Confirm leave/holiday/attendance scope.
9. Confirm current systems and system of record for employees/projects.
10. Confirm SAP product/version and integration requirement.
11. Confirm identity provider, hosting, security, data residency and retention.
12. Confirm report list and exact KPI definitions.
13. Confirm final MVP scope, acceptance owner and UAT participants.

---

## 24. Glossary

| Term | Definition |
| :--- | :--- |
| **Timesheet** | A user's recorded work entries for a defined period. |
| **Time entry** | One dated record of duration against a project/task. |
| **Billable** | Time eligible to be charged to a client under the agreed commercial rule; not automatically equivalent to invoiced revenue. |
| **Non-billable** | Time recorded but not chargeable to a client under the applicable rule. |
| **Utilisation** | A defined ratio of eligible recorded hours to an agreed capacity denominator; formula must be approved. |
| **Assignment** | Effective-dated permission/relationship allowing an employee to record time against a project. |
| **Approval** | Recorded decision by an authorised approver on a submitted timesheet. |
| **SAP workstream/module** | Configurable classification of the SAP-related work being performed. |
| **Audit event** | Append-only record of who performed an action, when, and what changed. |

---

## 25. Specification status and sign-off
This is a detailed baseline specification, not evidence that the client has approved every policy. Items labelled TBD or presented as recommendations must be validated. Changes after sign-off should be tracked with requirement ID, change reason, impact, owner and approval.

| Approval role | Name | Decision | Date |
| :--- | :--- | :--- | :--- |
| **Project Sponsor** | | Pending | |
| **PMO / Delivery** | | Pending | |
| **HR** | | Pending | |
| **Finance** | | Pending | |
| **IT / SAP** | | Pending | |