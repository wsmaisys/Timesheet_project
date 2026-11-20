import React, { useCallback, useEffect, useState } from 'react';
import { CheckCheck } from 'lucide-react';
import { Layout } from '../components/Layout';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { api, type NotificationItem } from '../lib/api';
import { formatUtcTimestamp } from '../lib/temporal';

export const NotificationsPage: React.FC = () => {
  const { user, refreshUnread } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.listNotifications({ limit: 100 });
      setItems(res.items);
      await refreshUnread();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load notifications.');
    }
  }, [refreshUnread]);

  useEffect(() => {
    void load();
  }, [load]);

  const markRead = async (id: string) => {
    await api.markNotificationRead(id);
    await load();
  };

  const markAllRead = async () => {
    await api.markAllNotificationsRead();
    await load();
  };

  return (
    <Layout
      title="Notifications"
      subtitle="Workflow updates for submissions, approvals, returns, and assignments"
      actions={
        <button type="button" className="btn btn-secondary btn-sm" onClick={markAllRead}>
          <CheckCheck size={15} aria-hidden="true" />
          <span>Mark all read</span>
        </button>
      }
    >
      {error ? (
        <div className="alert alert-danger" role="alert">
          <span>{error}</span>
        </div>
      ) : null}

      <section className="card">
        {items.length === 0 ? (
          <div className="alert alert-info" role="status">
            <span>You have no notifications.</span>
          </div>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {items.map((n) => (
              <li
                key={n.id}
                style={{
                  padding: '0.9rem 1rem',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  background: n.read_at ? 'var(--bg-surface)' : 'var(--brand-tint)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{n.title}</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    <span className="mono">{formatUtcTimestamp(n.created_at, user?.timezone)}</span> • Email outbox:{' '}
                    <StatusBadge status={n.delivery_status === 'SENT' ? 'ACTIVE' : n.delivery_status === 'FAILED' ? 'REJECTED' : 'DRAFT'} />
                  </div>
                </div>
                {!n.read_at ? (
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => void markRead(n.id)}>
                    Mark read
                  </button>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Read</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </Layout>
  );
};
