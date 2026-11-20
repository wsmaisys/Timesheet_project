import React, { useCallback, useEffect, useState } from 'react';
import { Check, RotateCcw, XCircle } from 'lucide-react';
import { FormField } from '../components/FormField';
import { Layout } from '../components/Layout';
import { ModalDialog } from '../components/ModalDialog';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { api, ApiClientError, type Timesheet } from '../lib/api';
import { formatHoursPair } from '../lib/format';
import { formatUtcTimestamp } from '../lib/temporal';

export const ApprovalsPage: React.FC = () => {
  const { user } = useAuth();
  const [pending, setPending] = useState<Timesheet[]>([]);
  const [approved, setApproved] = useState<Timesheet[]>([]);
  const [selected, setSelected] = useState<Timesheet | null>(null);
  const [actionMode, setActionMode] = useState<'REJECT' | 'REOPEN' | null>(null);
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadQueues = useCallback(async () => {
    try {
      const [pendRes, appRes] = await Promise.all([
        api.listPendingApprovals({ limit: 100 }),
        api.listTimesheets({ status: 'APPROVED', limit: 50 }),
      ]);
      setPending(pendRes.items);
      setApproved(appRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load approval queue.');
    }
  }, []);

  useEffect(() => {
    void loadQueues();
  }, [loadQueues]);

  const handleApprove = async (ts: Timesheet) => {
    setBusyId(ts.id);
    setError(null);
    setNotice(null);
    try {
      await api.approveTimesheet(ts.id, ts.version);
      setNotice(`Approved ${ts.user_name}'s timesheet (${ts.period_start}).`);
      await loadQueues();
    } catch (err) {
      setError(err instanceof ApiClientError ? `${err.message} (${err.code})` : 'Approval failed.');
    } finally {
      setBusyId(null);
    }
  };

  const openReasonDialog = (ts: Timesheet, mode: 'REJECT' | 'REOPEN') => {
    setSelected(ts);
    setActionMode(mode);
    setReason('');
  };

  const handleReasonSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !actionMode) return;
    setBusyId(selected.id);
    setError(null);
    try {
      if (actionMode === 'REJECT') {
        await api.rejectTimesheet(selected.id, reason.trim(), selected.version);
        setNotice(`Returned ${selected.user_name}'s timesheet with reason.`);
      } else {
        await api.reopenTimesheet(selected.id, reason.trim(), selected.version);
        setNotice(`Reopened ${selected.user_name}'s timesheet.`);
      }
      setActionMode(null);
      setSelected(null);
      await loadQueues();
    } catch (err) {
      setError(err instanceof ApiClientError ? `${err.message} (${err.code})` : 'Action failed.');
    } finally {
      setBusyId(null);
    }
  };

  const pendingColumns: TableColumn<Timesheet>[] = [
    {
      key: 'employee',
      label: 'Employee',
      isRowHeader: true,
      render: (ts) => (
        <div>
          <div style={{ fontWeight: 600 }}>{ts.user_name}</div>
          <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {ts.employee_code}
          </div>
        </div>
      ),
    },
    {
      key: 'period',
      label: 'Week Period',
      render: (ts) => (
        <span className="mono">
          {ts.period_start} .. {ts.period_end}
        </span>
      ),
    },
    {
      key: 'hours',
      label: 'Total / Billable',
      align: 'right',
      render: (ts) => (
        <div>
          <div className="mono" style={{ fontWeight: 700 }}>
            {formatHoursPair(ts.total_minutes)}
          </div>
          <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Billable: {formatHoursPair(ts.billable_minutes)}
          </div>
        </div>
      ),
    },
    {
      key: 'submitted',
      label: 'Submitted',
      render: (ts) => <span className="mono">{formatUtcTimestamp(ts.submitted_at, user?.timezone)}</span>,
    },
    {
      key: 'entries',
      label: 'Line Items',
      render: (ts) => (
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 600 }}>{ts.entries.length} entry row(s)</summary>
          <ul style={{ margin: '0.4rem 0 0', paddingInlineStart: '1rem', fontSize: '0.82rem' }}>
            {ts.entries.map((e) => (
              <li key={e.id}>
                {e.work_date} • {e.project_code}/{e.task_code} • {formatHoursPair(e.duration_minutes)} — {e.description}
              </li>
            ))}
          </ul>
        </details>
      ),
    },
    {
      key: 'actions',
      label: 'Decision',
      align: 'right',
      render: (ts) => (
        <div style={{ display: 'inline-flex', gap: '0.35rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busyId === ts.id}
            aria-label={`Approve timesheet for ${ts.user_name} week ${ts.period_start}`}
            onClick={() => handleApprove(ts)}
          >
            <Check size={14} aria-hidden="true" />
            <span>Approve</span>
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            disabled={busyId === ts.id}
            aria-label={`Reject timesheet for ${ts.user_name} week ${ts.period_start}`}
            onClick={() => openReasonDialog(ts, 'REJECT')}
          >
            <XCircle size={14} aria-hidden="true" />
            <span>Reject</span>
          </button>
        </div>
      ),
    },
  ];

  const approvedColumns: TableColumn<Timesheet>[] = [
    {
      key: 'employee',
      label: 'Employee',
      isRowHeader: true,
      render: (ts) => (
        <div>
          <div style={{ fontWeight: 600 }}>{ts.user_name}</div>
          <div className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {ts.employee_code}
          </div>
        </div>
      ),
    },
    { key: 'period', label: 'Week Period', render: (ts) => <span className="mono">{ts.period_start} .. {ts.period_end}</span> },
    { key: 'status', label: 'Status', render: (ts) => <StatusBadge status={ts.status} /> },
    { key: 'hours', label: 'Total', align: 'right', render: (ts) => <span className="mono">{formatHoursPair(ts.total_minutes)}</span> },
    { key: 'approved', label: 'Approved At', render: (ts) => <span className="mono">{formatUtcTimestamp(ts.approved_at, user?.timezone)}</span> },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (ts) =>
        ts.user_id !== user?.id ? (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            aria-label={`Reopen approved timesheet for ${ts.user_name} week ${ts.period_start}`}
            onClick={() => openReasonDialog(ts, 'REOPEN')}
          >
            <RotateCcw size={14} aria-hidden="true" />
            <span>Reopen</span>
          </button>
        ) : (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Own period</span>
        ),
    },
  ];

  return (
    <Layout title="Timesheet Approvals" subtitle="Review submitted team timesheets or reopen locked periods with an audited reason">
      {error ? (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      {notice ? (
        <div className="alert alert-success" role="status">
          <span>{notice}</span>
        </div>
      ) : null}

      <section className="card" aria-labelledby="pending-queue-heading">
        <div className="card-header">
          <h2 id="pending-queue-heading" className="card-title">
            Pending Approval Queue ({pending.length})
          </h2>
        </div>
        <ResponsiveTable
          caption="Submitted timesheets awaiting manager decision"
          columns={pendingColumns}
          rows={pending}
          getRowKey={(r) => r.id}
          emptyMessage="No pending timesheets require your approval right now."
        />
      </section>

      <section className="card" aria-labelledby="approved-history-heading">
        <div className="card-header">
          <h2 id="approved-history-heading" className="card-title">
            Recently Approved Timesheets
          </h2>
        </div>
        <ResponsiveTable
          caption="Locked approved timesheets within your approval scope"
          columns={approvedColumns}
          rows={approved}
          getRowKey={(r) => r.id}
          emptyMessage="No approved timesheets in scope yet."
        />
      </section>

      <ModalDialog
        open={Boolean(actionMode && selected)}
        title={actionMode === 'REJECT' ? 'Return Timesheet for Correction' : 'Reopen Locked Timesheet'}
        closedBy="closerequest"
        onClose={() => {
          setActionMode(null);
          setSelected(null);
        }}
      >
        <form onSubmit={handleReasonSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p style={{ fontSize: '0.9rem' }}>
            Target: <strong>{selected?.user_name}</strong> ({selected?.period_start} to {selected?.period_end})
          </p>
          <FormField
            id="decision-reason"
            label="Mandatory Reason"
            hint="Explain clearly what must be corrected (1-1000 characters)"
            errorText="A non-empty reason is required."
          >
            {(props) => (
              <textarea
                {...props}
                required
                autoFocus
                minLength={1}
                maxLength={1000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            )}
          </FormField>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setActionMode(null);
                setSelected(null);
              }}
            >
              Cancel
            </button>
            <button type="submit" className={actionMode === 'REJECT' ? 'btn btn-danger' : 'btn btn-primary'}>
              {actionMode === 'REJECT' ? 'Return Timesheet' : 'Confirm Reopen'}
            </button>
          </div>
        </form>
      </ModalDialog>
    </Layout>
  );
};
