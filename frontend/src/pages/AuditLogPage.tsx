import React, { useCallback, useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { ModalDialog } from '../components/ModalDialog';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { useAuth } from '../context/AuthContext';
import { api, type AuditEvent } from '../lib/api';
import { formatUtcTimestamp } from '../lib/temporal';

export const AuditLogPage: React.FC = () => {
  const { user } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [entityType, setEntityType] = useState('');
  const [action, setAction] = useState('');
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    try {
      const res = await api.listAuditEvents({
        entity_type: entityType || undefined,
        action: action || undefined,
        limit: 100,
      });
      setEvents(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load audit log.');
    }
  }, [entityType, action]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const columns: TableColumn<AuditEvent>[] = [
    {
      key: 'ts',
      label: 'Timestamp (UTC/Local)',
      isRowHeader: true,
      render: (e) => <span className="mono">{formatUtcTimestamp(e.created_at, user?.timezone)}</span>,
    },
    { key: 'actor', label: 'Actor', render: (e) => e.actor_email },
    { key: 'action', label: 'Action', render: (e) => <span className="role-chip">{e.action}</span> },
    { key: 'entity', label: 'Entity', render: (e) => <span className="mono">{e.entity_type}:{e.entity_id.slice(0, 8)}</span> },
    { key: 'req', label: 'Request ID', render: (e) => <span className="mono">{e.request_id}</span> },
    {
      key: 'diff',
      label: 'Payload',
      align: 'right',
      render: (e) => (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          aria-label={`Inspect audit payload for ${e.action} on ${e.entity_type}`}
          onClick={() => setSelected(e)}
        >
          Inspect
        </button>
      ),
    },
  ];

  return (
    <Layout title="Immutable Audit Trail" subtitle="Append-only log of workflow transitions, master data edits, and configuration changes">
      {error ? (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      <section className="card">
        <div className="form-grid" style={{ marginBottom: '1rem' }}>
          <div className="field">
            <label htmlFor="aud-entity">Entity Type</label>
            <select id="aud-entity" value={entityType} onChange={(e) => setEntityType(e.target.value)}>
              <option value="">All Entities</option>
              <option value="Timesheet">Timesheet</option>
              <option value="TimeEntry">TimeEntry</option>
              <option value="User">User</option>
              <option value="Project">Project</option>
              <option value="Task">Task</option>
              <option value="ProjectAssignment">ProjectAssignment</option>
              <option value="CompanySetting">CompanySetting</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="aud-action">Action Filter</label>
            <input
              id="aud-action"
              placeholder="e.g. TIMESHEET_APPROVED"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            />
          </div>
        </div>

        <ResponsiveTable caption="Audit events" columns={columns} rows={events} getRowKey={(r) => r.id} />
      </section>

      <ModalDialog
        open={Boolean(selected)}
        title={selected ? `Audit Event: ${selected.action}` : 'Audit Detail'}
        closedBy="any"
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.86rem' }}>
            <div>
              <strong>Actor:</strong> {selected.actor_email} • <strong>Request ID:</strong>{' '}
              <span className="mono">{selected.request_id}</span>
            </div>
            <div>
              <strong>Before:</strong>
              <pre style={{ background: 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', overflow: 'auto' }}>
                {JSON.stringify(selected.before_json, null, 2)}
              </pre>
            </div>
            <div>
              <strong>After:</strong>
              <pre style={{ background: 'var(--bg-subtle)', padding: '0.65rem', borderRadius: '6px', overflow: 'auto' }}>
                {JSON.stringify(selected.after_json, null, 2)}
              </pre>
            </div>
          </div>
        ) : null}
      </ModalDialog>
    </Layout>
  );
};
