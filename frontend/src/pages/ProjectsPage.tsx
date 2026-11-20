import React, { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
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
  type Client,
  type Project,
  type Task,
  type User,
} from '../lib/api';

type TabKey = 'projects' | 'tasks' | 'assignments' | 'clients';

export const ProjectsPage: React.FC = () => {
  const { user, settings } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const isAdminOrApprover = isAdmin || user?.role === 'APPROVER';

  const [tab, setTab] = useState<TabKey>('projects');
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Modals
  const [clientModal, setClientModal] = useState(false);
  const [clientCode, setClientCode] = useState('');
  const [clientName, setClientName] = useState('');

  const [projectModal, setProjectModal] = useState(false);
  const [projClientId, setProjClientId] = useState('');
  const [projCode, setProjCode] = useState('');
  const [projName, setProjName] = useState('');
  const [projStart, setProjStart] = useState('2026-01-01');
  const [projBillable, setProjBillable] = useState(true);
  const [projBudget, setProjBudget] = useState('');

  const [taskModal, setTaskModal] = useState(false);
  const [taskCode, setTaskCode] = useState('');
  const [taskName, setTaskName] = useState('');
  const [taskModule, setTaskModule] = useState('');
  const [taskWorkstream, setTaskWorkstream] = useState('');

  const [asgModal, setAsgModal] = useState(false);
  const [asgUserId, setAsgUserId] = useState('');
  const [asgProjectId, setAsgProjectId] = useState('');
  const [asgStart, setAsgStart] = useState('2026-01-01');
  const [asgAlloc, setAsgAlloc] = useState('50');

  const loadAll = useCallback(async () => {
    try {
      const [clRes, prRes, asgRes] = await Promise.all([
        api.listClients({ limit: 200 }),
        api.listProjects({ limit: 200 }),
        api.listAssignments({ limit: 200 }),
      ]);
      setClients(clRes.items);
      setProjects(prRes.items);
      setAssignments(asgRes.items);
      if (clRes.items[0] && !projClientId) setProjClientId(clRes.items[0].id);
      if (prRes.items[0] && !selectedProjectId) {
        setSelectedProjectId(prRes.items[0].id);
        setAsgProjectId(prRes.items[0].id);
      }
      if (isAdminOrApprover) {
        const uRes = await api.listUsers({ status: 'ACTIVE', limit: 200 });
        setUsers(uRes.items);
        if (uRes.items[0] && !asgUserId) setAsgUserId(uRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load master data.');
    }
  }, [isAdminOrApprover, projClientId, selectedProjectId, asgUserId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!selectedProjectId) return;
    api
      .listProjectTasks(selectedProjectId)
      .then(setTasks)
      .catch(() => setTasks([]));
  }, [selectedProjectId]);

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createClient({ code: clientCode, name: clientName });
      setClientModal(false);
      setClientCode('');
      setClientName('');
      setNotice('Client created.');
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not create client.');
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createProject({
        client_id: projClientId,
        code: projCode,
        name: projName,
        start_date: projStart,
        billable_default: projBillable,
        budget_hours: projBudget ? Number(projBudget) : null,
      });
      setProjectModal(false);
      setProjCode('');
      setProjName('');
      setNotice('Project created.');
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not create project.');
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setError(null);
    try {
      await api.createProjectTask(selectedProjectId, {
        code: taskCode,
        name: taskName,
        sap_module: taskModule || null,
        sap_workstream: taskWorkstream || null,
      });
      setTaskModal(false);
      setTaskCode('');
      setTaskName('');
      setNotice('Task created.');
      setTasks(await api.listProjectTasks(selectedProjectId));
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not create task.');
    }
  };

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createAssignment({
        user_id: asgUserId,
        project_id: asgProjectId,
        start_date: asgStart,
        allocation_percent: asgAlloc ? Number(asgAlloc) : null,
      });
      setAsgModal(false);
      setNotice('Employee assigned to project.');
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not create assignment.');
    }
  };

  const projectColumns: TableColumn<Project>[] = [
    { key: 'code', label: 'Code', isRowHeader: true, render: (p) => <span className="mono">{p.code}</span> },
    { key: 'name', label: 'Project Name', render: (p) => <strong>{p.name}</strong> },
    { key: 'client', label: 'Client', render: (p) => p.client_name },
    { key: 'dates', label: 'Dates', render: (p) => <span className="mono">{p.start_date} → {p.end_date || 'Open'}</span> },
    { key: 'billable', label: 'Billable Default', render: (p) => (p.billable_default ? 'Billable' : 'Non-Billable') },
    { key: 'status', label: 'Status', render: (p) => <StatusBadge status={p.status} /> },
  ];

  const taskColumns: TableColumn<Task>[] = [
    { key: 'code', label: 'Task Code', isRowHeader: true, render: (t) => <span className="mono">{t.code}</span> },
    { key: 'name', label: 'Task Name', render: (t) => t.name },
    { key: 'module', label: 'SAP Module', render: (t) => t.sap_module || '—' },
    { key: 'workstream', label: 'Workstream', render: (t) => t.sap_workstream || '—' },
    { key: 'status', label: 'Status', render: (t) => <StatusBadge status={t.status} /> },
  ];

  const asgColumns: TableColumn<Assignment>[] = [
    { key: 'user', label: 'Employee', isRowHeader: true, render: (a) => a.user_name },
    { key: 'project', label: 'Project', render: (a) => `${a.project_code} — ${a.project_name}` },
    { key: 'dates', label: 'Effective Dates', render: (a) => <span className="mono">{a.start_date} → {a.end_date || 'Ongoing'}</span> },
    { key: 'alloc', label: 'Allocation', align: 'right', render: (a) => (a.allocation_percent !== null ? `${a.allocation_percent}%` : '—') },
  ];

  const clientColumns: TableColumn<Client>[] = [
    { key: 'code', label: 'Client Code', isRowHeader: true, render: (c) => <span className="mono">{c.code}</span> },
    { key: 'name', label: 'Client Name', render: (c) => c.name },
    { key: 'status', label: 'Status', render: (c) => <StatusBadge status={c.status} /> },
  ];

  return (
    <Layout
      title="Projects, Tasks & Assignments"
      subtitle="SAP consulting engagements, configurable workstream classifications, and effective-dated employee staffing"
      actions={
        <>
          {isAdmin ? (
            <>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setClientModal(true)}>
                <Plus size={14} aria-hidden="true" />
                <span>New Client</span>
              </button>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setProjectModal(true)}>
                <Plus size={14} aria-hidden="true" />
                <span>New Project</span>
              </button>
            </>
          ) : null}
          {isAdminOrApprover ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAsgModal(true)}>
              <Plus size={14} aria-hidden="true" />
              <span>Assign Employee</span>
            </button>
          ) : null}
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

      <div className="tabs-bar" role="tablist" aria-label="Master data sections">
        {(['projects', 'tasks', 'assignments', 'clients'] as TabKey[]).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            className="tab-btn"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
          >
            {key === 'projects'
              ? `Projects (${projects.length})`
              : key === 'tasks'
                ? 'Project Tasks'
                : key === 'assignments'
                  ? `Assignments (${assignments.length})`
                  : `Clients (${clients.length})`}
          </button>
        ))}
      </div>

      {tab === 'projects' ? (
        <section className="card">
          <ResponsiveTable
            caption="Projects visible to your account"
            columns={projectColumns}
            rows={projects}
            getRowKey={(r) => r.id}
          />
        </section>
      ) : null}

      {tab === 'tasks' ? (
        <section className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="card-header" style={{ marginBottom: 0 }}>
            <div className="field" style={{ minInlineSize: '260px' }}>
              <label htmlFor="task-proj-select">Project</label>
              <select
                id="task-proj-select"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
            </div>
            {isAdminOrApprover && selectedProjectId ? (
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setTaskModal(true)}>
                <Plus size={14} aria-hidden="true" />
                <span>Add Task</span>
              </button>
            ) : null}
          </div>
          <ResponsiveTable caption="Project tasks and SAP classifications" columns={taskColumns} rows={tasks} getRowKey={(r) => r.id} />
        </section>
      ) : null}

      {tab === 'assignments' ? (
        <section className="card">
          <ResponsiveTable
            caption="Employee-to-project assignments"
            columns={asgColumns}
            rows={assignments}
            getRowKey={(r) => r.id}
          />
        </section>
      ) : null}

      {tab === 'clients' ? (
        <section className="card">
          <ResponsiveTable caption="Client organizations" columns={clientColumns} rows={clients} getRowKey={(r) => r.id} />
        </section>
      ) : null}

      <ModalDialog open={clientModal} title="Create Client" onClose={() => setClientModal(false)}>
        <form onSubmit={handleCreateClient} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <FormField id="cl-code" label="Client Code" errorText="Enter a unique client code.">
            {(p) => <input {...p} required autoFocus value={clientCode} onChange={(e) => setClientCode(e.target.value)} />}
          </FormField>
          <FormField id="cl-name" label="Client Name" errorText="Enter client name.">
            {(p) => <input {...p} required value={clientName} onChange={(e) => setClientName(e.target.value)} />}
          </FormField>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setClientModal(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create Client</button>
          </div>
        </form>
      </ModalDialog>

      <ModalDialog open={projectModal} title="Create Project" onClose={() => setProjectModal(false)}>
        <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <FormField id="pr-client" label="Client" errorText="Select an active client.">
            {(p) => (
              <select {...p} required autoFocus value={projClientId} onChange={(e) => setProjClientId(e.target.value)}>
                {clients.filter((c) => c.status === 'ACTIVE').map((c) => (
                  <option key={c.id} value={c.id}>{c.code} — {c.name}</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="pr-code" label="Project Code" errorText="Enter unique project code.">
            {(p) => <input {...p} required value={projCode} onChange={(e) => setProjCode(e.target.value)} />}
          </FormField>
          <FormField id="pr-name" label="Project Name" errorText="Enter project name.">
            {(p) => <input {...p} required value={projName} onChange={(e) => setProjName(e.target.value)} />}
          </FormField>
          <FormField id="pr-start" label="Start Date" errorText="Select start date.">
            {(p) => <input {...p} type="date" required value={projStart} onChange={(e) => setProjStart(e.target.value)} />}
          </FormField>
          <FormField id="pr-budget" label="Budget Hours (Optional)" errorText="Enter a non-negative number.">
            {(p) => <input {...p} type="number" min={0} step="0.5" value={projBudget} onChange={(e) => setProjBudget(e.target.value)} />}
          </FormField>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input id="pr-bill" type="checkbox" checked={projBillable} onChange={(e) => setProjBillable(e.target.checked)} />
            <label htmlFor="pr-bill" style={{ fontWeight: 600, fontSize: '0.9rem' }}>Billable by default</label>
          </div>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setProjectModal(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create Project</button>
          </div>
        </form>
      </ModalDialog>

      <ModalDialog open={taskModal} title="Add Project Task" onClose={() => setTaskModal(false)}>
        <form onSubmit={handleCreateTask} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <FormField id="tk-code" label="Task Code" errorText="Enter unique task code.">
            {(p) => <input {...p} required autoFocus value={taskCode} onChange={(e) => setTaskCode(e.target.value)} />}
          </FormField>
          <FormField id="tk-name" label="Task Name" errorText="Enter task name.">
            {(p) => <input {...p} required value={taskName} onChange={(e) => setTaskName(e.target.value)} />}
          </FormField>
          <FormField id="tk-mod" label="SAP Module (Optional)" errorText="Select valid module.">
            {(p) => (
              <select {...p} value={taskModule} onChange={(e) => setTaskModule(e.target.value)}>
                <option value="">None</option>
                {(settings?.sap_modules || []).map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="tk-ws" label="SAP Workstream (Optional)" errorText="Select valid workstream.">
            {(p) => (
              <select {...p} value={taskWorkstream} onChange={(e) => setTaskWorkstream(e.target.value)}>
                <option value="">None</option>
                {(settings?.sap_workstreams || []).map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            )}
          </FormField>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setTaskModal(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create Task</button>
          </div>
        </form>
      </ModalDialog>

      <ModalDialog open={asgModal} title="Assign Employee to Project" onClose={() => setAsgModal(false)}>
        <form onSubmit={handleCreateAssignment} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <FormField id="asg-user" label="Employee" errorText="Select an active employee.">
            {(p) => (
              <select {...p} required autoFocus value={asgUserId} onChange={(e) => setAsgUserId(e.target.value)}>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name} ({u.employee_code})</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="asg-proj" label="Project" errorText="Select a project.">
            {(p) => (
              <select {...p} required value={asgProjectId} onChange={(e) => setAsgProjectId(e.target.value)}>
                {projects.filter((pr) => pr.status !== 'CLOSED').map((pr) => (
                  <option key={pr.id} value={pr.id}>{pr.code} — {pr.name}</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="asg-start" label="Effective Start Date" errorText="Select start date.">
            {(p) => <input {...p} type="date" required value={asgStart} onChange={(e) => setAsgStart(e.target.value)} />}
          </FormField>
          <FormField id="asg-alloc" label="Allocation % (Optional)" errorText="Enter 0 to 100.">
            {(p) => <input {...p} type="number" min={0} max={100} value={asgAlloc} onChange={(e) => setAsgAlloc(e.target.value)} />}
          </FormField>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setAsgModal(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create Assignment</button>
          </div>
        </form>
      </ModalDialog>
    </Layout>
  );
};
