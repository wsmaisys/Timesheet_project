import React, { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
import { FormField } from '../components/FormField';
import { Layout } from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { api, ApiClientError, type CompanySettings } from '../lib/api';

export const SettingsPage: React.FC = () => {
  const { settings, refreshSettings } = useAuth();
  const [form, setForm] = useState<CompanySettings | null>(settings);
  const [modulesText, setModulesText] = useState('');
  const [workstreamsText, setWorkstreamsText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setForm(s);
        setModulesText(s.sap_modules.join(', '));
        setWorkstreamsText(s.sap_workstreams.join(', '));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load settings.'));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const sap_modules = modulesText
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean);
      const sap_workstreams = workstreamsText
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean);

      const updated = await api.updateSettings({
        ...form,
        sap_modules,
        sap_workstreams,
      });
      setForm(updated);
      await refreshSettings();
      setNotice('Company settings saved and audited.');
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout
      title="Company Configuration"
      subtitle="Configure working week boundaries, time increments, deadlines, policies, and SAP taxonomy"
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

      {form ? (
        <form onSubmit={handleSave} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="form-grid">
            <FormField id="cfg-week-start" label="Week Start Day" errorText="Select week start day.">
              {(p) => (
                <select
                  {...p}
                  value={form.week_start_day}
                  onChange={(e) => setForm({ ...form, week_start_day: Number(e.target.value) })}
                >
                  <option value={0}>Monday</option>
                  <option value={6}>Sunday</option>
                  <option value={5}>Saturday</option>
                </select>
              )}
            </FormField>

            <FormField id="cfg-inc" label="Time Entry Increment" errorText="Select increment.">
              {(p) => (
                <select
                  {...p}
                  value={form.entry_increment_minutes}
                  onChange={(e) =>
                    setForm({ ...form, entry_increment_minutes: Number(e.target.value) as CompanySettings['entry_increment_minutes'] })
                  }
                >
                  {[5, 6, 15, 30, 60].map((v) => (
                    <option key={v} value={v}>
                      {v} minutes
                    </option>
                  ))}
                </select>
              )}
            </FormField>

            <FormField id="cfg-exp-daily" label="Expected Daily Minutes" errorText="Enter minutes (60-1440).">
              {(p) => (
                <input
                  {...p}
                  type="number"
                  min={60}
                  max={1440}
                  value={form.expected_daily_minutes}
                  onChange={(e) => setForm({ ...form, expected_daily_minutes: Number(e.target.value) })}
                />
              )}
            </FormField>

            <FormField id="cfg-exp-weekly" label="Expected Weekly Minutes" errorText="Enter minutes (60-10080).">
              {(p) => (
                <input
                  {...p}
                  type="number"
                  min={60}
                  max={10080}
                  value={form.expected_weekly_minutes}
                  onChange={(e) => setForm({ ...form, expected_weekly_minutes: Number(e.target.value) })}
                />
              )}
            </FormField>

            <FormField id="cfg-max-daily" label="Max Daily Minutes" errorText="Enter minutes (60-1440).">
              {(p) => (
                <input
                  {...p}
                  type="number"
                  min={60}
                  max={1440}
                  value={form.max_daily_minutes}
                  onChange={(e) => setForm({ ...form, max_daily_minutes: Number(e.target.value) })}
                />
              )}
            </FormField>

            <FormField id="cfg-tz" label="Default Timezone" errorText="Enter valid IANA timezone.">
              {(p) => (
                <input
                  {...p}
                  required
                  value={form.default_timezone}
                  onChange={(e) => setForm({ ...form, default_timezone: e.target.value })}
                />
              )}
            </FormField>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={form.allow_billable_override}
                onChange={(e) => setForm({ ...form, allow_billable_override: e.target.checked })}
              />
              <span>Allow employees to override project billable default</span>
            </label>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={form.allow_duplicate_entries}
                onChange={(e) => setForm({ ...form, allow_duplicate_entries: e.target.checked })}
              />
              <span>Allow identical duplicate entries on the same day</span>
            </label>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={form.require_minimum_hours_on_submit}
                onChange={(e) => setForm({ ...form, require_minimum_hours_on_submit: e.target.checked })}
              />
              <span>Require minimum expected weekly hours to submit</span>
            </label>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={form.allow_self_approval}
                onChange={(e) => setForm({ ...form, allow_self_approval: e.target.checked })}
              />
              <span>Allow delegated self-approval</span>
            </label>
          </div>

          <FormField
            id="cfg-sap-modules"
            label="Configurable SAP Modules"
            hint="Comma-separated list (administered without code changes)"
            errorText="Provide at least one SAP module."
          >
            {(p) => (
              <input {...p} required value={modulesText} onChange={(e) => setModulesText(e.target.value)} />
            )}
          </FormField>

          <FormField
            id="cfg-sap-workstreams"
            label="Configurable SAP Workstreams"
            hint="Comma-separated list"
            errorText="Provide at least one SAP workstream."
          >
            {(p) => (
              <input {...p} required value={workstreamsText} onChange={(e) => setWorkstreamsText(e.target.value)} />
            )}
          </FormField>

          <div>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save size={16} aria-hidden="true" />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </form>
      ) : (
        <p>Loading configuration...</p>
      )}
    </Layout>
  );
};
