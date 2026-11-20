import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, Shield } from 'lucide-react';
import { FormField } from '../components/FormField';
import { useAuth } from '../context/AuthContext';
import { ApiClientError } from '../lib/api';

const DEMO_ACCOUNTS = [
  { label: 'Employee (Meera)', email: 'consultant@sapconsult.example.com' },
  { label: 'Manager (Rohan)', email: 'manager@sapconsult.example.com' },
  { label: 'Admin (Ananya)', email: 'admin@sapconsult.example.com' },
  { label: 'Viewer (Priya)', email: 'director@sapconsult.example.com' },
];

export const LoginPage: React.FC = () => {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    document.title = 'Sign In | Chronos Timesheet';
    if (user) {
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate('/', { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(`${err.message} (${err.code})`);
      } else {
        setError('Unable to reach authentication service.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const quickFill = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('DemoPass123!');
    setError(null);
    setSubmitting(true);
    try {
      await login(demoEmail, 'DemoPass123!');
      navigate('/', { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-shell">
      <div className="login-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="brand-mark" aria-hidden="true">
            CT
          </div>
          <div>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Chronos Timesheet</h1>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              SAP Consulting Workforce &amp; Approval Platform
            </p>
          </div>
        </div>

        {error ? (
          <div className="alert alert-danger" role="alert">
            <span>{error}</span>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <FormField
            id="login-email"
            label="Work Email"
            hint="Format: name@sapconsult.example.com"
            errorText="Enter a valid corporate email address."
          >
            {(props) => (
              <input
                {...props}
                type="email"
                name="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            )}
          </FormField>

          <FormField
            id="login-password"
            label="Password"
            hint="Minimum 8 characters"
            errorText="Enter your account password (at least 8 characters)."
          >
            {(props) => (
              <input
                {...props}
                type="password"
                name="password"
                required
                minLength={8}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </FormField>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            <LogIn size={16} aria-hidden="true" />
            <span>{submitting ? 'Signing in...' : 'Sign in'}</span>
          </button>
        </form>

        <div className="alert alert-info" style={{ fontSize: '0.82rem' }}>
          <Shield size={16} aria-hidden="true" style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>
            Enterprise SSO (Microsoft Entra ID / SAP IAS) adapter ready; local JWT credentials active for baseline deployment.
          </span>
        </div>

        <div className="demo-accounts">
          <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Demo / UAT Quick Sign-In (Password: <code>DemoPass123!</code>)
          </p>
          <div className="demo-grid">
            {DEMO_ACCOUNTS.map((acct) => (
              <button
                key={acct.email}
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={submitting}
                onClick={() => quickFill(acct.email)}
              >
                {acct.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
};
