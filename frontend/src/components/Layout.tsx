import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Bell,
  CalendarClock,
  CheckSquare,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface LayoutProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ title, subtitle, actions, children }) => {
  const { user, unreadCount, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    document.title = `${title} | Chronos Timesheet`;
  }, [title]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) return null;

  const isAdmin = user.role === 'ADMIN';
  const isApprover = user.role === 'APPROVER' || isAdmin;

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, show: true },
    { to: '/timesheet', label: 'My Timesheet', icon: CalendarClock, show: true },
    { to: '/approvals', label: 'Approvals', icon: CheckSquare, show: isApprover },
    { to: '/projects', label: 'Projects & Tasks', icon: FolderKanban, show: true },
    { to: '/reports', label: 'Reports & Export', icon: BarChart3, show: true },
    {
      to: '/notifications',
      label: 'Notifications',
      icon: Bell,
      show: true,
      badge: unreadCount > 0 ? unreadCount : undefined,
    },
    { to: '/users', label: 'Users', icon: Users, show: isAdmin },
    { to: '/settings', label: 'Company Settings', icon: Settings, show: isAdmin },
    { to: '/audit', label: 'Audit Log', icon: ShieldCheck, show: isAdmin },
  ];

  return (
    <div className="app-shell">
      <a href="#main-heading" className="skip-link visually-hidden">
        Skip to main content
      </a>

      <aside className={`app-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            CT
          </div>
          <div>
            <div className="brand-title">Chronos</div>
            <div className="brand-subtitle">SAP Practice Timesheet</div>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm mobile-menu-btn"
            style={{ color: '#e2e8f0', marginInlineStart: 'auto' }}
            aria-label="Close navigation menu"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <nav aria-label="Primary">
          <ul className="nav-list">
            {navItems
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/'}
                      className="nav-link"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <span className="nav-link-inner">
                        <Icon size={17} aria-hidden="true" />
                        <span>{item.label}</span>
                      </span>
                      {item.badge ? (
                        <span className="nav-badge" aria-label={`${item.badge} unread`}>
                          {item.badge}
                        </span>
                      ) : null}
                    </NavLink>
                  </li>
                );
              })}
          </ul>
        </nav>
      </aside>

      <header className="app-header">
        <button
          type="button"
          className="btn btn-secondary btn-sm mobile-menu-btn"
          aria-label="Open navigation menu"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={18} aria-hidden="true" />
          <span>Menu</span>
        </button>

        <div className="header-actions">
          <div className="user-pill">
            <span>{user.full_name}</span>
            <span className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
              {user.employee_code}
            </span>
            <span className="role-chip">{user.role}</span>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
            <LogOut size={15} aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </header>

      <main className="app-main">
        <div className="page-header">
          <div>
            <h1 id="main-heading" tabIndex={-1} className="page-title">
              {title}
            </h1>
            {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
          </div>
          {actions ? <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>{actions}</div> : null}
        </div>
        {children}
      </main>
    </div>
  );
};
