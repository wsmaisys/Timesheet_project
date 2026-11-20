export type UserRole = 'EMPLOYEE' | 'APPROVER' | 'ADMIN' | 'MANAGEMENT_VIEWER';
export type ActiveStatus = 'ACTIVE' | 'INACTIVE';
export type ProjectStatus = 'DRAFT' | 'ACTIVE' | 'ON_HOLD' | 'CLOSED';
export type TimesheetStatus = 'DRAFT' | 'SUBMITTED' | 'REJECTED' | 'APPROVED' | 'REOPENED' | 'CANCELLED';

export interface ErrorDetail {
  field: string;
  issue: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: ErrorDetail[];
    request_id?: string;
  };
}

export class ApiClientError extends Error {
  status: number;
  code: string;
  details: ErrorDetail[];
  requestId?: string;

  constructor(status: number, code: string, message: string, details: ErrorDetail[] = [], requestId?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export interface User {
  id: string;
  employee_code: string;
  email: string;
  full_name: string;
  role: UserRole;
  status: ActiveStatus;
  manager_id: string | null;
  department: string | null;
  timezone: string;
  expected_daily_minutes: number | null;
  expected_weekly_minutes: number | null;
  can_override_assignment: boolean;
}

export interface CompanySettings {
  week_start_day: number;
  default_timezone: string;
  expected_daily_minutes: number;
  expected_weekly_minutes: number;
  entry_increment_minutes: 5 | 6 | 15 | 30 | 60;
  max_daily_minutes: number;
  submission_deadline_day: number;
  submission_deadline_time: string;
  allow_billable_override: boolean;
  allow_duplicate_entries: boolean;
  allow_self_approval: boolean;
  allow_overlapping_assignments: boolean;
  require_minimum_hours_on_submit: boolean;
  max_export_rows: number;
  sap_modules: string[];
  sap_workstreams: string[];
}

export interface Client {
  id: string;
  code: string;
  name: string;
  status: ActiveStatus;
}

export interface Project {
  id: string;
  client_id: string;
  client_name: string;
  code: string;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string | null;
  status: ProjectStatus;
  project_manager_id: string | null;
  billable_default: boolean;
  budget_hours: number | null;
  version: number;
}

export interface Task {
  id: string;
  project_id: string;
  code: string;
  name: string;
  status: ActiveStatus;
  sap_workstream: string | null;
  sap_module: string | null;
}

export interface Assignment {
  id: string;
  user_id: string;
  user_name: string;
  project_id: string;
  project_code: string;
  project_name: string;
  start_date: string;
  end_date: string | null;
  allocation_percent: number | null;
}

export interface TimeEntry {
  id: string;
  work_date: string;
  project_id: string;
  project_code: string;
  project_name: string;
  task_id: string;
  task_code: string;
  task_name: string;
  sap_module: string | null;
  sap_workstream: string | null;
  duration_minutes: number;
  billable: boolean;
  description: string;
}

export interface ApprovalEvent {
  id: string;
  timesheet_id: string;
  actor_id: string;
  actor_name: string;
  action: 'APPROVED' | 'REJECTED' | 'REOPENED';
  reason: string | null;
  created_at: string;
}

export interface Timesheet {
  id: string;
  user_id: string;
  user_name: string;
  employee_code: string;
  period_start: string;
  period_end: string;
  status: TimesheetStatus;
  notes: string | null;
  assigned_approver_id: string | null;
  total_minutes: number;
  billable_minutes: number;
  entries: TimeEntry[];
  approval_events: ApprovalEvent[];
  submitted_at: string | null;
  approved_at: string | null;
  version: number;
}

export interface ReportRow {
  user_id: string;
  employee_code: string;
  employee_name: string;
  department: string | null;
  project_id: string;
  project_code: string;
  project_name: string;
  billable_minutes: number;
  non_billable_minutes: number;
  total_minutes: number;
}

export interface AuditEvent {
  id: string;
  actor_id: string | null;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  request_id: string;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  title: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  delivery_status: 'PENDING' | 'SENT' | 'FAILED';
  created_at: string;
}

export interface PageMeta {
  limit: number;
  offset: number;
  total: number;
}

export interface PagedResponse<T> {
  items: T[];
  meta: PageMeta;
}

export interface DashboardSummary {
  role: UserRole;
  current_period: {
    period_start: string;
    period_end: string;
    week_start_day: number;
    entry_increment_minutes: number;
  };
  employee_summary: {
    current_timesheet_id: string | null;
    current_status: string;
    current_week_minutes: number;
    expected_weekly_minutes: number;
    active_assignments_count: number;
    returned_timesheets_count: number;
    unread_notifications_count: number;
    recent_weeks: Array<{
      id: string;
      period_start: string;
      period_end: string;
      status: TimesheetStatus;
      total_minutes: number;
    }>;
  } | null;
  manager_summary: {
    pending_approvals_count: number;
    direct_reports_count: number;
    current_week_submitted_count: number;
    current_week_missing_count: number;
  } | null;
  admin_summary: {
    active_users_count: number;
    active_projects_count: number;
    submitted_waiting_count: number;
    projects_ending_soon: Array<{ id: string; code: string; name: string; end_date: string }>;
  } | null;
  management_summary: {
    month_start: string;
    as_of_date: string;
    billable_minutes: number;
    non_billable_minutes: number;
    total_minutes: number;
    department_scope: string;
  } | null;
  metric_definitions: Record<string, unknown>;
}

const TOKEN_STORAGE_KEY = 'chronos_tokens_v1';

export interface StoredTokens {
  access: string;
  refresh: string;
}

export function getStoredTokens(): StoredTokens | null {
  try {
    const raw = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredTokens;
  } catch {
    return null;
  }
}

export function setStoredTokens(tokens: StoredTokens | null): void {
  if (!tokens) {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } else {
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function tryRefreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  const tokens = getStoredTokens();
  if (!tokens?.refresh) return null;

  refreshPromise = (async () => {
    try {
      const res = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: tokens.refresh }),
      });
      if (!res.ok) {
        setStoredTokens(null);
        return null;
      }
      const data = (await res.json()) as { access: string; refresh?: string };
      setStoredTokens({
        access: data.access,
        refresh: data.refresh || tokens.refresh,
      });
      return data.access;
    } catch {
      setStoredTokens(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  retryOn401 = true,
): Promise<T> {
  const tokens = getStoredTokens();
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (tokens?.access && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${tokens.access}`);
  }

  const res = await fetch(`/api/v1${path}`, { ...options, headers });

  if (res.status === 401 && retryOn401 && tokens?.refresh && !path.startsWith('/auth/')) {
    const nextAccess = await tryRefreshAccessToken();
    if (nextAccess) {
      headers.set('Authorization', `Bearer ${nextAccess}`);
      return apiRequest<T>(path, { ...options, headers }, false);
    }
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get('Content-Type') || '';
  if (!res.ok) {
    if (contentType.includes('application/json')) {
      const payload = (await res.json()) as ApiErrorBody;
      throw new ApiClientError(
        res.status,
        payload?.error?.code || 'INTERNAL_ERROR',
        payload?.error?.message || `Request failed with status ${res.status}`,
        payload?.error?.details || [],
        payload?.error?.request_id,
      );
    }
    throw new ApiClientError(res.status, 'INTERNAL_ERROR', `Request failed with status ${res.status}`);
  }

  if (contentType.includes('text/csv')) {
    return (await res.blob()) as unknown as T;
  }

  return (await res.json()) as T;
}

export function buildQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') {
      qs.set(k, String(v));
    }
  }
  const encoded = qs.toString();
  return encoded ? `?${encoded}` : '';
}

export const api = {
  login: (email: string, password: string) =>
    apiRequest<{ access: string; refresh: string; user: User; permissions: string[] }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  logout: (refresh?: string) =>
    apiRequest<void>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify(refresh ? { refresh } : {}),
    }),
  me: () => apiRequest<{ user: User; permissions: string[] }>('/auth/me'),
  dashboard: () => apiRequest<DashboardSummary>('/dashboard'),
  getSettings: () => apiRequest<CompanySettings>('/settings'),
  updateSettings: (payload: Partial<CompanySettings>) =>
    apiRequest<CompanySettings>('/settings', { method: 'PATCH', body: JSON.stringify(payload) }),
  listUsers: (params?: { role?: string; status?: string; search?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<User>>(`/users${buildQueryString(params || {})}`),
  createUser: (payload: Record<string, unknown>) =>
    apiRequest<User>('/users', { method: 'POST', body: JSON.stringify(payload) }),
  updateUser: (id: string, payload: Record<string, unknown>) =>
    apiRequest<User>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listClients: (params?: { status?: string; search?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<Client>>(`/clients${buildQueryString(params || {})}`),
  createClient: (payload: { code: string; name: string }) =>
    apiRequest<Client>('/clients', { method: 'POST', body: JSON.stringify(payload) }),
  updateClient: (id: string, payload: { name?: string; status?: ActiveStatus }) =>
    apiRequest<Client>(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listProjects: (params?: { status?: string; client_id?: string; search?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<Project>>(`/projects${buildQueryString(params || {})}`),
  createProject: (payload: Record<string, unknown>) =>
    apiRequest<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: Record<string, unknown>) =>
    apiRequest<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listProjectTasks: (projectId: string, status?: ActiveStatus) =>
    apiRequest<Task[]>(`/projects/${projectId}/tasks${buildQueryString({ status })}`),
  createProjectTask: (projectId: string, payload: Record<string, unknown>) =>
    apiRequest<Task>(`/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify(payload) }),
  updateProjectTask: (projectId: string, taskId: string, payload: Record<string, unknown>) =>
    apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listAssignments: (params?: { user_id?: string; project_id?: string; active_on?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<Assignment>>(`/assignments${buildQueryString(params || {})}`),
  createAssignment: (payload: Record<string, unknown>) =>
    apiRequest<Assignment>('/assignments', { method: 'POST', body: JSON.stringify(payload) }),
  updateAssignment: (id: string, payload: Record<string, unknown>) =>
    apiRequest<Assignment>(`/assignments/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  listTimesheets: (params?: { status?: string; period_start?: string; period_end?: string; user_id?: string; project_id?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<Timesheet>>(`/timesheets${buildQueryString(params || {})}`),
  createTimesheet: (payload: { period_start: string; period_end: string; notes?: string | null }, idempotencyKey?: string) =>
    apiRequest<Timesheet>('/timesheets', {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
      body: JSON.stringify(payload),
    }),
  getTimesheet: (id: string) => apiRequest<Timesheet>(`/timesheets/${id}`),
  updateTimesheet: (id: string, payload: { notes?: string | null; version?: number }) =>
    apiRequest<Timesheet>(`/timesheets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  addTimeEntry: (timesheetId: string, payload: Record<string, unknown>, idempotencyKey?: string) =>
    apiRequest<TimeEntry>(`/timesheets/${timesheetId}/entries`, {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
      body: JSON.stringify(payload),
    }),
  updateTimeEntry: (timesheetId: string, entryId: string, payload: Record<string, unknown>) =>
    apiRequest<TimeEntry>(`/timesheets/${timesheetId}/entries/${entryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteTimeEntry: (timesheetId: string, entryId: string) =>
    apiRequest<void>(`/timesheets/${timesheetId}/entries/${entryId}`, { method: 'DELETE' }),
  submitTimesheet: (timesheetId: string, version?: number, idempotencyKey?: string) =>
    apiRequest<Timesheet>(`/timesheets/${timesheetId}/submit`, {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
      body: JSON.stringify(version ? { version } : {}),
    }),
  listPendingApprovals: (params?: { limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<Timesheet>>(`/approvals/pending${buildQueryString(params || {})}`),
  approveTimesheet: (timesheetId: string, version?: number) =>
    apiRequest<Timesheet>(`/timesheets/${timesheetId}/approve`, {
      method: 'POST',
      body: JSON.stringify(version ? { version } : {}),
    }),
  rejectTimesheet: (timesheetId: string, reason: string, version?: number) =>
    apiRequest<Timesheet>(`/timesheets/${timesheetId}/reject`, {
      method: 'POST',
      body: JSON.stringify(version ? { reason, version } : { reason }),
    }),
  reopenTimesheet: (timesheetId: string, reason: string, version?: number) =>
    apiRequest<Timesheet>(`/timesheets/${timesheetId}/reopen`, {
      method: 'POST',
      body: JSON.stringify(version ? { reason, version } : { reason }),
    }),
  getTimeSummary: (params: { from_date: string; to_date: string; project_id?: string; user_id?: string; billable?: boolean; status?: string }) =>
    apiRequest<ReportRow[]>(`/reports/time-summary${buildQueryString(params)}`),
  exportTimeSummary: (params: { from_date: string; to_date: string; project_id?: string; user_id?: string; billable?: boolean; status?: string }) =>
    apiRequest<Blob>(`/reports/time-summary/export${buildQueryString(params)}`),
  listNotifications: (params?: { unread_only?: boolean; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<NotificationItem> & { unread_count: number }>(`/notifications${buildQueryString(params || {})}`),
  markNotificationRead: (id: string) =>
    apiRequest<NotificationItem>(`/notifications/${id}/read`, { method: 'POST', body: '{}' }),
  markAllNotificationsRead: () =>
    apiRequest<{ marked_count: number }>('/notifications/read-all', { method: 'POST', body: '{}' }),
  listAuditEvents: (params?: { entity_type?: string; action?: string; from_date?: string; to_date?: string; limit?: number; offset?: number }) =>
    apiRequest<PagedResponse<AuditEvent>>(`/audit-events${buildQueryString(params || {})}`),
};
