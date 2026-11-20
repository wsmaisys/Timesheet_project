import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, CheckSquare, Clock } from 'lucide-react';
import { Layout } from '../components/Layout';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { api, type DashboardSummary } from '../lib/api';
import { formatHoursPair, formatMinutesHHMM } from '../lib/format';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load dashboard.'));
  }, []);

  const emp = data?.employee_summary;
  const mgr = data?.manager_summary;
  const adm = data?.admin_summary;
  const mgmt = data?.management_summary;

  const recentCols: TableColumn<{
    id: string;
    period_start: string;
    period_end: string;
    status: string;
    total_minutes: number;
  }>[] = [
    {
      key: 'period',
      label: 'Week Period',
      isRowHeader: true,
      render: (r) => (
        <Link to={`/timesheet?week=${r.period_start}`} style={{ fontWeight: 600, color: 'var(--brand-primary)' }}>
          {r.period_start} to {r.period_end}
        </Link>
      ),
    },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    {
      key: 'hours',
      label: 'Logged Time',
      align: 'right',
      render: (r) => <span className="mono">{formatHoursPair(r.total_minutes)}</span>,
    },
  ];

  return (
    <Layout
      title={`Welcome, ${user?.full_name || ''}`}
      subtitle={
        data
          ? `Current week: ${data.current_period.period_start} to ${data.current_period.period_end} • Increment: ${data.current_period.entry_increment_minutes}m`
          : 'Loading workspace overview...'
      }
      actions={
        <>
          <Link to="/timesheet" className="btn btn-primary">
            <Clock size={16} aria-hidden="true" />
            <span>Open My Timesheet</span>
          </Link>
          {mgr ? (
            <Link to="/approvals" className="btn btn-secondary">
              <CheckSquare size={16} aria-hidden="true" />
              <span>Approvals ({mgr.pending_approvals_count})</span>
            </Link>
          ) : null}
        </>
      }
    >
      {error ? (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      {emp && emp.returned_timesheets_count > 0 ? (
        <div className="alert alert-warning" role="status">
          <AlertTriangle size={18} aria-hidden="true" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Action needed:</strong> You have {emp.returned_timesheets_count} returned timesheet(s) requiring
            correction.{' '}
            <Link to="/timesheet" style={{ fontWeight: 700, color: 'inherit' }}>
              Review in My Timesheet <ArrowRight size={14} aria-hidden="true" style={{ verticalAlign: 'middle' }} />
            </Link>
          </div>
        </div>
      ) : null}

      {emp ? (
        <section aria-labelledby="emp-kpis-heading">
          <h2 id="emp-kpis-heading" className="visually-hidden">
            Personal Timesheet Summary
          </h2>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">This Week Logged</span>
              <span className="kpi-value mono">{formatMinutesHHMM(emp.current_week_minutes)}</span>
              <span className="kpi-meta">Target: {formatHoursPair(emp.expected_weekly_minutes)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Current Week Status</span>
              <div style={{ marginTop: '0.2rem' }}>
                <StatusBadge status={emp.current_status === 'NOT_CREATED' ? 'DRAFT' : emp.current_status} />
              </div>
              <span className="kpi-meta">
                {emp.current_status === 'NOT_CREATED' ? 'Not started yet' : 'Current canonical period'}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Active Assignments</span>
              <span className="kpi-value mono">{emp.active_assignments_count}</span>
              <span className="kpi-meta">Projects open for time entry today</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Unread Alerts</span>
              <span className="kpi-value mono">{emp.unread_notifications_count}</span>
              <span className="kpi-meta">
                <Link to="/notifications" style={{ color: 'var(--brand-primary)' }}>
                  View inbox
                </Link>
              </span>
            </div>
          </div>
        </section>
      ) : null}

      {mgr ? (
        <section className="card" aria-labelledby="mgr-summary-heading">
          <div className="card-header">
            <h2 id="mgr-summary-heading" className="card-title">
              Manager Approval Oversight
            </h2>
            <Link to="/approvals" className="btn btn-secondary btn-sm">
              Review Queue
            </Link>
          </div>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Pending Approvals</span>
              <span className="kpi-value mono">{mgr.pending_approvals_count}</span>
              <span className="kpi-meta">Awaiting your decision</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Team Members</span>
              <span className="kpi-value mono">{mgr.direct_reports_count}</span>
              <span className="kpi-meta">Active direct reports</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Submitted This Week</span>
              <span className="kpi-value mono">{mgr.current_week_submitted_count}</span>
              <span className="kpi-meta">Submitted or approved</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Not Yet Submitted</span>
              <span className="kpi-value mono">{mgr.current_week_missing_count}</span>
              <span className="kpi-meta">Pending employee action</span>
            </div>
          </div>
        </section>
      ) : null}

      {adm ? (
        <section className="card" aria-labelledby="adm-summary-heading">
          <div className="card-header">
            <h2 id="adm-summary-heading" className="card-title">
              Platform Administration Overview
            </h2>
            <Link to="/settings" className="btn btn-secondary btn-sm">
              Configure Policies
            </Link>
          </div>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Active Users</span>
              <span className="kpi-value mono">{adm.active_users_count}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Active Projects</span>
              <span className="kpi-value mono">{adm.active_projects_count}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Pending Queue</span>
              <span className="kpi-value mono">{adm.submitted_waiting_count}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Projects Ending Soon</span>
              <span className="kpi-value mono">{adm.projects_ending_soon.length}</span>
              <span className="kpi-meta">Within 30 days</span>
            </div>
          </div>
        </section>
      ) : null}

      {mgmt ? (
        <section className="card" aria-labelledby="mgmt-summary-heading">
          <div className="card-header">
            <h2 id="mgmt-summary-heading" className="card-title">
              Month-to-Date Utilisation Snapshot ({mgmt.month_start} to {mgmt.as_of_date})
            </h2>
            <span className="role-chip">Scope: {mgmt.department_scope}</span>
          </div>
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Billable Hours</span>
              <span className="kpi-value mono">{formatHoursPair(mgmt.billable_minutes)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Non-Billable Hours</span>
              <span className="kpi-value mono">{formatHoursPair(mgmt.non_billable_minutes)}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Recorded</span>
              <span className="kpi-value mono">{formatHoursPair(mgmt.total_minutes)}</span>
            </div>
          </div>
        </section>
      ) : null}

      {emp ? (
        <section className="card" aria-labelledby="recent-weeks-heading">
          <div className="card-header">
            <h2 id="recent-weeks-heading" className="card-title">
              Recent Weekly Timesheets
            </h2>
          </div>
          <ResponsiveTable
            caption="Your recent timesheet periods and approval status"
            columns={recentCols}
            rows={emp.recent_weeks}
            getRowKey={(r) => r.id}
            emptyMessage="No timesheets created yet. Open My Timesheet to start logging hours."
          />
        </section>
      ) : null}
    </Layout>
  );
};
