import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  api,
  type CompanySettings,
  getStoredTokens,
  setStoredTokens,
  type User,
} from '../lib/api';

interface AuthContextValue {
  user: User | null;
  permissions: string[];
  settings: CompanySettings | null;
  unreadCount: number;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  refreshSettings: () => Promise<void>;
  refreshUnread: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const refreshUnread = useCallback(async () => {
    try {
      const data = await api.listNotifications({ unread_only: true, limit: 1 });
      setUnreadCount(data.unread_count);
    } catch {
      // Ignore transient poll errors
    }
  }, []);

  const refreshSettings = useCallback(async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch {
      // Ignore if unauthenticated
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    const tokens = getStoredTokens();
    if (!tokens?.access) {
      setUser(null);
      setPermissions([]);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me.user);
      setPermissions(me.permissions);
      await Promise.all([refreshSettings(), refreshUnread()]);
    } catch {
      setStoredTokens(null);
      setUser(null);
      setPermissions([]);
    } finally {
      setLoading(false);
    }
  }, [refreshSettings, refreshUnread]);

  useEffect(() => {
    void refreshProfile();
  }, [refreshProfile]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      setStoredTokens({ access: res.access, refresh: res.refresh });
      setUser(res.user);
      setPermissions(res.permissions);
      await Promise.all([refreshSettings(), refreshUnread()]);
    },
    [refreshSettings, refreshUnread],
  );

  const logout = useCallback(async () => {
    const tokens = getStoredTokens();
    try {
      if (tokens?.access) {
        await api.logout(tokens.refresh);
      }
    } catch {
      // Clear local session regardless
    } finally {
      setStoredTokens(null);
      setUser(null);
      setPermissions([]);
      setSettings(null);
      setUnreadCount(0);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        permissions,
        settings,
        unreadCount,
        loading,
        login,
        logout,
        refreshProfile,
        refreshSettings,
        refreshUnread,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
