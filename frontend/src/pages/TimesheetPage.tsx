import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Edit2,
  Plus,
  Send,
  Trash2,
} from 'lucide-react';
import { FormField } from '../components/FormField';
import { Layout } from '../components/Layout';
import { ModalDialog } from '../components/ModalDialog';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import {
  api,
  ApiClientError,
  type Assignment,
  type Project,
  type Task,
  type TimeEntry,
  type Timesheet,
} from '../lib/api';
import { formatHoursPair, formatMinutesHHMM } from '../lib/format';
import {
  addDays,
  formatCalendarDate,
  formatUtcTimestamp,
  getWeekDates,
  getWeekStart,
  todayPlainDate,
} from '../lib/temporal';

const EDITABLE_STATUSES = new Set(['DRAFT', 'REJECTED', 'REOPENED']);

export const TimesheetPage: React.FC = () => {
  const { user, settings } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const weekStartDay = settings?.week_start_day ?? 0;
  const increment = settings?.entry_increment_minutes ?? 15;
  const expectedWeekly = user?.expected_weekly_minutes ?? settings?.expected_weekly_minutes ?? 2400;

  const initialPeriodStart = useMemo(() => {
    const param = searchParams.get('week');
    const anchor = param || todayPlainDate(user?.timezone);
    return getWeekStart(anchor, weekStartDay);
  }, [searchParams, user?.timezone, weekStartDay]);

  const [periodStart, setPeriodStart] = useState(initialPeriodStart);
  const periodEnd = useMemo(() => addDays(periodStart, 6), [periodStart]);
  const weekDates = useMemo(() => getWeekDates(periodStart), [periodStart]);

  const [timesheet, setTimesheet] = useState<Timesheet | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [tasksByProject, setTasksByProject] = useState<Record<string, Task[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Entry modal state
  const [entryModalOpen, setEntryModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimeEntry | null>(null);
  const [workDate, setWorkDate] = useState(periodStart);
  const [projectId, setProjectId] = useState('');
  const [taskId, setTaskId] = useState('');
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [billable, setBillable] = useState(true);
  const [description, setDescription] = useState('');
  const [savingEntry, setSavingEntry] = useState(false);

  // Submit confirmation modal state
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [submittingWeek, setSubmittingWeek] = useState(false);

  const loadTasksForProject = useCallback(
    async (pid: string) => {
      if (!pid || tasksByProject[pid]) return;
      try {
        const list = await api.listProjectTasks(pid, 'ACTIVE');
        setTasksByProject((prev) => ({ ...prev, [pid]: list }));
      } catch {
        // Ignore task fetch error
      }
    },
    [tasksByProject],
  );

  const loadWeek = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [tsRes, projRes, asgRes] = await Promise.all([
        api.listTimesheets({
          user_id: user.id,
          period_start: periodStart,
          period_end: periodEnd,
        }),
        api.listProjects({ status: 'ACTIVE', limit: 200 }),
        api.listAssignments({ user_id: user.id, limit: 200 }),
      ]);
      const match = tsRes.items.find((t) => t.period_start === periodStart) || null;
      setTimesheet(match);
      setProjects(projRes.items);
      setAssignments(asgRes.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load timesheet data.');
    } finally {
      setLoading(false);
    }
  }, [user, periodStart, periodEnd]);

  useEffect(() => {
    void loadWeek();
  }, [loadWeek]);

  const changeWeek = (deltaDays: number) => {
    const next = addDays(periodStart, deltaDays);
    setPeriodStart(next);
    setSearchParams({ week: next });
    setNotice(null);
  };

  const jumpToCurrentWeek = () => {
    const current = getWeekStart(todayPlainDate(user?.timezone), weekStartDay);
    setPeriodStart(current);
    setSearchParams({ week: current });
    setNotice(null);
  };

  const handleCreateDraft = async () => {
    setError(null);
    try {
      const created = await api.createTimesheet(
        { period_start: periodStart, period_end: periodEnd },
        `create-${periodStart}`,
      );
      setTimesheet(created);
      setNotice('Created weekly draft timesheet.');
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not create timesheet.');
    }
  };

  const eligibleProjects = useMemo(() => {
    if (user?.can_override_assignment) return projects;
    return projects.filter((p) =>
      assignments.some(
        (a) =>
          a.project_id === p.id &&
          a.start_date <= workDate &&
          (!a.end_date || a.end_date >= workDate),
      ),
    );
  }, [projects, assignments, workDate, user?.can_override_assignment]);

  const openAddEntryModal = async (dateOverride?: string) => {
    let activeTs = timesheet;
    if (!activeTs) {
      try {
        activeTs = await api.createTimesheet(
          { period_start: periodStart, period_end: periodEnd },
          `create-${periodStart}`,
        );
        setTimesheet(activeTs);
      } catch (err) {
        setError(err instanceof ApiClientError ? err.message : 'Could not initialize draft timesheet.');
        return;
      }
    }

    const defaultDate = dateOverride || periodStart;
    setEditingEntry(null);
    setWorkDate(defaultDate);
    setDurationMinutes(Math.max(increment, 60 - (60 % increment)));
    setDescription('');
    const firstProj = projects.find(
      (p) =>
        user?.can_override_assignment ||
        assignments.some(
          (a) => a.project_id === p.id && a.start_date <= defaultDate && (!a.end_date || a.end_date >= defaultDate),
        ),
    );
    if (firstProj) {
      setProjectId(firstProj.id);
      setBillable(firstProj.billable_default);
      await loadTasksForProject(firstProj.id);
      const tasks = tasksByProject[firstProj.id] || (await api.listProjectTasks(firstProj.id, 'ACTIVE'));
      setTasksByProject((prev) => ({ ...prev, [firstProj.id]: tasks }));
      setTaskId(tasks[0]?.id || '');
    } else {
      setProjectId('');
      setTaskId('');
    }
    setEntryModalOpen(true);
  };

  const openEditEntryModal = async (entry: TimeEntry) => {
    setEditingEntry(entry);
    setWorkDate(entry.work_date);
    setProjectId(entry.project_id);
    await loadTasksForProject(entry.project_id);
    setTaskId(entry.task_id);
    setDurationMinutes(entry.duration_minutes);
    setBillable(entry.billable);
    setDescription(entry.description);
    setEntryModalOpen(true);
  };

  const handleProjectChange = async (nextPid: string) => {
    setProjectId(nextPid);
    const proj = projects.find((p) => p.id === nextPid);
    if (proj) {
      setBillable(proj.billable_default);
    }
    if (nextPid) {
      const list = tasksByProject[nextPid] || (await api.listProjectTasks(nextPid, 'ACTIVE'));
      setTasksByProject((prev) => ({ ...prev, [nextPid]: list }));
      setTaskId(list[0]?.id || '');
    } else {
      setTaskId('');
    }
  };

  const handleSaveEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!timesheet) return;
    setSavingEntry(true);
    setError(null);
    try {
      const payload = {
        work_date: workDate,
        project_id: projectId,
        task_id: taskId,
        duration_minutes: Number(durationMinutes),
        billable,
        description: description.trim(),
      };
      if (editingEntry) {
        await api.updateTimeEntry(timesheet.id, editingEntry.id, payload);
        setNotice('Updated time entry.');
      } else {
        await api.addTimeEntry(timesheet.id, payload);
        setNotice('Added time entry.');
      }
      setEntryModalOpen(false);
      await loadWeek();
    } catch (err) {
      setError(err instanceof ApiClientError ? `${err.message} (${err.code})` : 'Failed to save entry.');
    } finally {
      setSavingEntry(false);
    }
  };

  const handleDeleteEntry = async (entry: TimeEntry) => {
    if (!timesheet) return;
    setError(null);
    try {
      await api.deleteTimeEntry(timesheet.id, entry.id);
      setNotice(`Deleted entry for ${entry.work_date}.`);
      await loadWeek();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Failed to delete entry.');
    }
  };

  const handleSubmitTimesheet = async () => {
    if (!timesheet) return;
    setSubmittingWeek(true);
    setError(null);
    try {
      const updated = await api.submitTimesheet(timesheet.id, timesheet.version);
      setTimesheet(updated);
      setSubmitModalOpen(false);
      setNotice('Timesheet submitted for approval.');
    } catch (err) {
      setError(err instanceof ApiClientError ? `${err.message} (${err.code})` : 'Submission failed.');
      setSubmitModalOpen(false);
    } finally {
      setSubmittingWeek(false);
    }
  };

  const isEditable = !timesheet || EDITABLE_STATUSES.has(timesheet.status);
  const totalMinutes = timesheet?.total_minutes ?? 0;
  const pct = Math.min(100, Math.round((totalMinutes / Math.max(1, expectedWeekly)) * 100));

  const latestRejection = timesheet?.approval_events
    ?.slice()
    .reverse()
    .find((ev) => ev.action === 'REJECTED' || ev.action === 'REOPENED');

  const dayTotals = useMemo(() => {
    const map: Record<string, number> = {};
    for (const d of weekDates) map[d] = 0;
    for (const entry of timesheet?.entries || []) {
      map[entry.work_date] = (map[entry.work_date] || 0) + entry.duration_minutes;
    }
    return map;
  }, [weekDates, timesheet]);

  const entryColumns: TableColumn<TimeEntry>[] = [
    {
      key: 'date',
      label: 'Work Date',
      isRowHeader: true,
      render: (e) => <span className="mono">{formatCalendarDate(e.work_date)}</span>,
    },
    {
      key: 'project',
      label: 'Project / Task',
      render: (e) => (
        <div>
          <div style={{ fontWeight: 600 }}>
            {e.project_code} — {e.project_name}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {e.task_code}: {e.task_name}
            {e.sap_module ? ` • SAP ${e.sap_module}` : ''}
            {e.sap_workstream ? ` (${e.sap_workstream})` : ''}
          </div>
        </div>
      ),
    },
    {
      key: 'description',
      label: 'Description',
      render: (e) => <span>{e.description}</span>,
    },
    {
      key: 'billable',
      label: 'Billable',
      render: (e) => (
        <span className={`status-badge ${e.billable ? 'status-APPROVED' : 'status-DRAFT'}`}>
          {e.billable ? 'Billable' : 'Non-Billable'}
        </span>
      ),
    },
    {
      key: 'duration',
      label: 'Duration',
      align: 'right',
      render: (e) => <span className="mono">{formatHoursPair(e.duration_minutes)}</span>,
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (e) =>
        isEditable ? (
          <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              aria-label={`Edit entry on ${e.work_date} for ${e.project_code}`}
              onClick={() => openEditEntryModal(e)}
            >
              <Edit2 size={14} aria-hidden="true" />
              <span>Edit</span>
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              aria-label={`Delete entry on ${e.work_date} for ${e.project_code}`}
              onClick={() => handleDeleteEntry(e)}
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>
        ) : (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Locked</span>
        ),
    },
  ];

  const availableTasks = tasksByProject[projectId] || [];

  return (
    <Layout
      title="My Weekly Timesheet"
      subtitle={`Period ${periodStart} to ${periodEnd} (${user?.timezone || 'UTC'})`}
      actions={
        <>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => changeWeek(-7)}>
            <ChevronLeft size={16} aria-hidden="true" />
            <span>Prev Week</span>
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={jumpToCurrentWeek}>
            <span>This Week</span>
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => changeWeek(7)}>
            <span>Next Week</span>
            <ChevronRight size={16} aria-hidden="true" />
          </button>
        </>
      }
    >
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

      {timesheet?.status === 'REJECTED' && latestRejection?.reason ? (
        <div className="alert alert-danger" role="alert">
          <AlertTriangle size={18} aria-hidden="true" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Returned by {latestRejection.actor_name}:</strong> {latestRejection.reason}
          </div>
        </div>
      ) : null}

      {timesheet?.status === 'REOPENED' && latestRejection?.reason ? (
        <div className="alert alert-warning" role="status">
          <AlertTriangle size={18} aria-hidden="true" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Reopened by {latestRejection.actor_name}:</strong> {latestRejection.reason}
          </div>
        </div>
      ) : null}

      <section className="card" aria-label="Weekly summary and actions">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <StatusBadge status={timesheet?.status || 'DRAFT'} />
            <span className="mono" style={{ fontWeight: 700, fontSize: '1.05rem' }}>
              {formatHoursPair(totalMinutes)}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
              of {formatHoursPair(expectedWeekly)} target ({pct}%)
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {!timesheet ? (
              <button type="button" className="btn btn-secondary" onClick={handleCreateDraft}>
                Initialize Draft Week
              </button>
            ) : null}
            {isEditable ? (
              <button type="button" className="btn btn-primary" onClick={() => openAddEntryModal(periodStart)}>
                <Plus size={16} aria-hidden="true" />
                <span>Add Time Entry</span>
              </button>
            ) : null}
            {timesheet && isEditable && timesheet.entries.length > 0 ? (
              <button type="button" className="btn btn-secondary" onClick={() => setSubmitModalOpen(true)}>
                <Send size={15} aria-hidden="true" />
                <span>Submit Week</span>
              </button>
            ) : null}
          </div>
        </div>

        <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(115px, 1fr))',
            gap: '0.5rem',
            marginTop: '1rem',
          }}
        >
          {weekDates.map((d) => (
            <button
              key={d}
              type="button"
              className="btn btn-secondary btn-sm"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                padding: '0.55rem 0.7rem',
                blockSize: 'auto',
              }}
              disabled={!isEditable}
              onClick={() => openAddEntryModal(d)}
            >
              <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>{formatCalendarDate(d)}</span>
              <span className="mono" style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                {formatMinutesHHMM(dayTotals[d] || 0)}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="card" aria-labelledby="entries-heading">
        <div className="card-header">
          <h2 id="entries-heading" className="card-title">
            Time Entries
          </h2>
          {timesheet ? (
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Billable: <strong className="mono">{formatHoursPair(timesheet.billable_minutes)}</strong> • Version{' '}
              <span className="mono">{timesheet.version}</span>
            </span>
          ) : null}
        </div>

        {loading ? (
          <p>Loading weekly entries...</p>
        ) : (
          <ResponsiveTable
            caption={`Time entries for ${periodStart} to ${periodEnd}`}
            columns={entryColumns}
            rows={timesheet?.entries || []}
            getRowKey={(r) => r.id}
            emptyMessage="No time entries logged for this week yet. Click Add Time Entry or pick a day tile above."
          />
        )}
      </section>

      {timesheet && timesheet.approval_events.length > 0 ? (
        <section className="card" aria-labelledby="history-heading">
          <h2 id="history-heading" className="card-title" style={{ marginBottom: '0.75rem' }}>
            Approval &amp; Decision History
          </h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {timesheet.approval_events.map((ev) => (
              <li
                key={ev.id}
                style={{
                  padding: '0.65rem 0.85rem',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}
              >
                <div>
                  <StatusBadge status={ev.action} /> <strong style={{ marginInlineStart: '0.4rem' }}>{ev.actor_name}</strong>
                  {ev.reason ? <p style={{ marginTop: '0.25rem', fontSize: '0.88rem' }}>{ev.reason}</p> : null}
                </div>
                <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {formatUtcTimestamp(ev.created_at, user?.timezone)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ModalDialog
        open={entryModalOpen}
        title={editingEntry ? 'Edit Time Entry' : 'Add Time Entry'}
        closedBy="closerequest"
        onClose={() => setEntryModalOpen(false)}
      >
        <form id="time-entry-form" onSubmit={handleSaveEntry} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <FormField id="entry-date" label="Work Date" hint={`Must be within ${periodStart} to ${periodEnd}`} errorText="Select a valid date inside this week.">
            {(props) => (
              <select
                {...props}
                required
                autoFocus
                value={workDate}
                onChange={(e) => setWorkDate(e.target.value)}
              >
                {weekDates.map((d) => (
                  <option key={d} value={d}>
                    {d} ({formatCalendarDate(d)})
                  </option>
                ))}
              </select>
            )}
          </FormField>

          <FormField id="entry-project" label="Assigned Project" errorText="Select an active assigned project.">
            {(props) => (
              <select
                {...props}
                required
                value={projectId}
                onChange={(e) => void handleProjectChange(e.target.value)}
              >
                <option value="">Select project...</option>
                {eligibleProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>

          <FormField id="entry-task" label="Task / Work Item" errorText="Select a task belonging to the chosen project.">
            {(props) => (
              <select
                {...props}
                required
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
              >
                <option value="">Select task...</option>
                {availableTasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.code} — {t.name} {t.sap_module ? `(${t.sap_module})` : ''}
                  </option>
                ))}
              </select>
            )}
          </FormField>

          <FormField
            id="entry-duration"
            label="Duration (Minutes)"
            hint={`Enter a positive multiple of ${increment} minutes (e.g. 60 = 1h, 480 = 8h)`}
            errorText={`Duration must be a positive multiple of ${increment} minutes.`}
          >
            {(props) => (
              <input
                {...props}
                type="number"
                required
                min={increment}
                max={settings?.max_daily_minutes ?? 960}
                step={increment}
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
              />
            )}
          </FormField>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              id="entry-billable"
              type="checkbox"
              checked={billable}
              disabled={!settings?.allow_billable_override}
              onChange={(e) => setBillable(e.target.checked)}
            />
            <label htmlFor="entry-billable" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              Billable to client {!settings?.allow_billable_override ? '(locked to project default)' : ''}
            </label>
          </div>

          <FormField
            id="entry-description"
            label="Work Description"
            hint="Briefly describe the consulting activity completed (1-1000 chars)"
            errorText="Enter a non-empty description of work performed."
          >
            {(props) => (
              <textarea
                {...props}
                required
                minLength={1}
                maxLength={1000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            )}
          </FormField>

          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setEntryModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={savingEntry}>
              {savingEntry ? 'Saving...' : editingEntry ? 'Save Changes' : 'Add Entry'}
            </button>
          </div>
        </form>
      </ModalDialog>

      <ModalDialog
        open={submitModalOpen}
        title="Submit Weekly Timesheet?"
        closedBy="closerequest"
        onClose={() => setSubmitModalOpen(false)}
        footer={
          <>
            <button type="button" className="btn btn-secondary" autoFocus onClick={() => setSubmitModalOpen(false)}>
              Cancel
            </button>
            <button type="button" className="btn btn-primary" disabled={submittingWeek} onClick={handleSubmitTimesheet}>
              {submittingWeek ? 'Submitting...' : 'Confirm Submission'}
            </button>
          </>
        }
      >
        <p>
          You are submitting <strong className="mono">{formatHoursPair(totalMinutes)}</strong> for period{' '}
          <strong>
            {periodStart} to {periodEnd}
          </strong>
          . Once submitted, entries are locked while awaiting manager approval.
        </p>
      </ModalDialog>
    </Layout>
  );
};
