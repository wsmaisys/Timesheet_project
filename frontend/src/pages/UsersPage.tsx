import React, { useCallback, useEffect, useState } from 'react';
import { Plus, UserCheck, UserX } from 'lucide-react';
import { FormField } from '../components/FormField';
import { Layout } from '../components/Layout';
import { ModalDialog } from '../components/ModalDialog';
import { ResponsiveTable, type TableColumn } from '../components/ResponsiveTable';
import { StatusBadge } from '../components/StatusBadge';
import { api, ApiClientError, type User, type UserRole } from '../lib/api';

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [employeeCode, setEmployeeCode] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('DemoPass123!');
  const [role, setRole] = useState<UserRole>('EMPLOYEE');
  const [managerId, setManagerId] = useState('');
  const [department, setDepartment] = useState('SAP Delivery');
  const [timezone, setTimezone] = useState('UTC');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    try {
      const res = await api.listUsers({ limit: 200 });
      setUsers(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load users.');
    }
  }, []);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createUser({
        employee_code: employeeCode.trim(),
        email: email.trim(),
        full_name: fullName.trim(),
        password,
        role,
        manager_id: managerId || null,
        department: department.trim() || null,
        timezone: timezone.trim() || 'UTC',
      });
      setModalOpen(false);
      setEmployeeCode('');
      setEmail('');
      setFullName('');
      setNotice('User account created.');
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? `${err.message} (${err.code})` : 'Failed to create user.');
    }
  };

  const toggleUserStatus = async (target: User) => {
    setError(null);
    const nextStatus = target.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.updateUser(target.id, { status: nextStatus });
      setNotice(`${target.full_name} marked ${nextStatus}.`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Could not update status.');
    }
  };

  const approverChoices = users.filter((u) => (u.role === 'APPROVER' || u.role === 'ADMIN') && u.status === 'ACTIVE');

  const columns: TableColumn<User>[] = [
    {
      key: 'name',
      label: 'Employee',
      isRowHeader: true,
      render: (u) => (
        <div>
          <div style={{ fontWeight: 600 }}>{u.full_name}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{u.email}</div>
        </div>
      ),
    },
    { key: 'code', label: 'Code', render: (u) => <span className="mono">{u.employee_code}</span> },
    { key: 'role', label: 'Role', render: (u) => <span className="role-chip">{u.role}</span> },
    { key: 'dept', label: 'Department', render: (u) => u.department || '—' },
    { key: 'tz', label: 'Timezone', render: (u) => <span className="mono">{u.timezone}</span> },
    { key: 'status', label: 'Status', render: (u) => <StatusBadge status={u.status} /> },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (u) => (
        <button
          type="button"
          className={`btn btn-sm ${u.status === 'ACTIVE' ? 'btn-danger' : 'btn-secondary'}`}
          aria-label={`${u.status === 'ACTIVE' ? 'Deactivate' : 'Reactivate'} user ${u.full_name}`}
          onClick={() => void toggleUserStatus(u)}
        >
          {u.status === 'ACTIVE' ? <UserX size={14} aria-hidden="true" /> : <UserCheck size={14} aria-hidden="true" />}
          <span>{u.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}</span>
        </button>
      ),
    },
  ];

  return (
    <Layout
      title="User Administration"
      subtitle="Manage employee directory, roles, manager hierarchy, and soft deactivation"
      actions={
        <button type="button" className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <Plus size={16} aria-hidden="true" />
          <span>New User</span>
        </button>
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

      <section className="card">
        <ResponsiveTable caption="Platform users and RBAC assignments" columns={columns} rows={users} getRowKey={(r) => r.id} />
      </section>

      <ModalDialog open={modalOpen} title="Create User Account" onClose={() => setModalOpen(false)}>
        <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <FormField id="u-code" label="Employee Code" errorText="Enter a unique employee code.">
            {(p) => <input {...p} required autoFocus value={employeeCode} onChange={(e) => setEmployeeCode(e.target.value)} />}
          </FormField>
          <FormField id="u-name" label="Full Name" errorText="Enter full name.">
            {(p) => <input {...p} required value={fullName} onChange={(e) => setFullName(e.target.value)} />}
          </FormField>
          <FormField id="u-email" label="Work Email" hint="Format: user@sapconsult.example.com" errorText="Enter a valid work email.">
            {(p) => <input {...p} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />}
          </FormField>
          <FormField id="u-pass" label="Initial Password" hint="Minimum 8 characters" errorText="Password must be at least 8 characters.">
            {(p) => <input {...p} type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />}
          </FormField>
          <FormField id="u-role" label="Role" errorText="Select user role.">
            {(p) => (
              <select {...p} value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
                <option value="EMPLOYEE">EMPLOYEE</option>
                <option value="APPROVER">APPROVER</option>
                <option value="ADMIN">ADMIN</option>
                <option value="MANAGEMENT_VIEWER">MANAGEMENT_VIEWER</option>
              </select>
            )}
          </FormField>
          <FormField id="u-mgr" label="Primary Approver / Manager (Optional)" errorText="Invalid manager.">
            {(p) => (
              <select {...p} value={managerId} onChange={(e) => setManagerId(e.target.value)}>
                <option value="">None</option>
                {approverChoices.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name} ({m.employee_code})
                  </option>
                ))}
              </select>
            )}
          </FormField>
          <FormField id="u-dept" label="Department" errorText="Invalid department.">
            {(p) => <input {...p} value={department} onChange={(e) => setDepartment(e.target.value)} />}
          </FormField>
          <FormField id="u-tz" label="IANA Timezone" hint="Example: UTC, Asia/Kolkata, Europe/Berlin" errorText="Enter valid IANA timezone.">
            {(p) => <input {...p} required value={timezone} onChange={(e) => setTimezone(e.target.value)} />}
          </FormField>
          <div className="dialog-footer" style={{ marginInline: '-1.25rem', marginBottom: '-1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary">Create User</button>
          </div>
        </form>
      </ModalDialog>
    </Layout>
  );
};
