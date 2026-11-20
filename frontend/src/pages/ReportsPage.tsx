import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, Filter } from 'lucide-react';
import { Layout } from '../components/Layout';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { useAuth } from '../context/AuthContext';
import { api, ApiClientError, type Project, type ReportRow } from '../lib/api';
import { formatHoursPair, triggerCsvDownload } from '../lib/format';
import { getMonthStart, todayPlainDate } from '../lib/temporal';

export const ReportsPage: React.FC = () => {
  const { user } = useAuth();
  const today = useMemo(() => todayPlainDate(user?.timezone), [user?.timezone]);
  const [fromDate, setFromDate] = useState(() => getMonthStart(today));
  const [toDate, setToDate] = useState(today);
  const [projectId, setProjectId] = useState('');
  const [billable, setBillable] = useState<'all' | 'true' | 'false'>('all');
  const [status, setStatus] = useState('');

  const [projects, setProjects] = useState<Project[]>([]);
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const runReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTimeSummary({
        from_date: fromDate,
        to_date: toDate,
        project_id: projectId || undefined,
        billable: billable === 'all' ? undefined : billable === 'true',
        status: status || undefined,
      });
      setRows(data);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Unable to generate report.');
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, projectId, billable, status]);

  useEffect(() => {
    api
      .listProjects({ limit: 200 })
      .then((res) => setProjects(res.items))
      .catch(() => setProjects([]));
    void runReport();
  }, [runReport]);

  const handleExport = async () => {
    setError(null);
    try {
      const blob = await api.exportTimeSummary({
        from_date: fromDate,
        to_date: toDate,
        project_id: projectId || undefined,
        billable: billable === 'all' ? undefined : billable === 'true',
        status: status || undefined,
      });
      triggerCsvDownload(blob, `time-summary-${fromDate}-to-${toDate}.csv`);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'CSV export failed.');
    }
  };

  const totals = useMemo(() => {
    let bill = 0;
    let nonBill = 0;
    for (const r of rows) {
      bill += r.billable_minutes;
      nonBill += r.non_billable_minutes;
    }
    return { bill, nonBill, total: bill + nonBill };
  }, [rows]);

  const billPct = totals.total > 0 ? Math.round((totals.bill / totals.total) * 100) : 0;

  const columns: TableColumn<ReportRow>[] = [
    {
      key: 'employee',
      label: 'Employee',
      isRowHeader: true,
      render: (r) => (
        <div>
          <div style={{ fontWeight: 600 }}>{r.employee_name}</div>
          <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {r.employee_code} {r.department ? `• ${r.department}` : ''}
          </div>
        </div>
      ),
    },
    {
      key: 'project',
      label: 'Project',
      render: (r) => `${r.project_code} — ${r.project_name}`,
    },
    {
      key: 'billable',
      label: 'Billable',
      align: 'right',
      render: (r) => <span className="mono">{formatHoursPair(r.billable_minutes)}</span>,
    },
    {
      key: 'non_billable',
      label: 'Non-Billable',
      align: 'right',
      render: (r) => <span className="mono">{formatHoursPair(r.non_billable_minutes)}</span>,
    },
    {
      key: 'total',
      label: 'Total Hours',
      align: 'right',
      render: (r) => <strong className="mono">{formatHoursPair(r.total_minutes)}</strong>,
    },
  ];

  return (
    <Layout
      title="Time Summary & CSV Export"
      subtitle="Row-level scoped utilisation totals by employee, project, and billable classification"
      actions={
        <button type="button" className="btn btn-primary" onClick={handleExport}>
          <Download size={16} aria-hidden="true" />
          <span>Export CSV</span>
        </button>
      }
    >
      {error ? (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      <section className="card" aria-label="Report filters">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void runReport();
          }}
          className="form-grid"
        >
          <div className="field">
            <label htmlFor="rpt-from">From Date</label>
            <input id="rpt-from" type="date" required value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="rpt-to">To Date</label>
            <input id="rpt-to" type="date" required value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="rpt-project">Project</label>
            <select id="rpt-project" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">All visible projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="rpt-billable">Billable Filter</label>
            <select
              id="rpt-billable"
              value={billable}
              onChange={(e) => setBillable(e.target.value as 'all' | 'true' | 'false')}
            >
              <option value="all">All</option>
              <option value="true">Billable Only</option>
              <option value="false">Non-Billable Only</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="rpt-status">Timesheet Status</label>
            <select id="rpt-status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All Active States</option>
              <option value="APPROVED">Approved Only</option>
              <option value="SUBMITTED">Submitted Only</option>
              <option value="DRAFT">Draft Only</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button type="submit" className="btn btn-secondary">
              <Filter size={15} aria-hidden="true" />
              <span>Apply Filters</span>
            </button>
          </div>
        </form>
      </section>

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Total Hours</span>
          <span className="kpi-value mono">{formatHoursPair(totals.total)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Billable Hours</span>
          <span className="kpi-value mono">{formatHoursPair(totals.bill)}</span>
          <span className="kpi-meta">{billPct}% of total</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Non-Billable Hours</span>
          <span className="kpi-value mono">{formatHoursPair(totals.nonBill)}</span>
        </div>
      </div>

      <section className="card">
        {loading ? (
          <p>Calculating scoped report...</p>
        ) : (
          <ResponsiveTable
            caption={`Time summary from ${fromDate} to ${toDate}`}
            columns={columns}
            rows={rows}
            getRowKey={(r) => `${r.user_id}-${r.project_id}`}
            emptyMessage="No time entries match the selected filters."
          />
        )}
      </section>
    </Layout>
  );
};
