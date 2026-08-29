import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CONFIG } from '../config';
import { DemoUser } from '../types/api';
import { Role } from '../types/enums';
import { authApi } from '../api/auth';

interface AuthState {
  user: DemoUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (role: Role) => Promise<void>;
  logout: () => void;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

function parseJwtExp(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const exp = parseJwtExp(token);
  if (!exp) return false; // If no exp claim, assume valid
  const now = Math.floor(Date.now() / 1000);
  return exp <= now;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem(CONFIG.AUTH_STORAGE_KEY);
  }, []);

  // Rehydrate on boot and check expiration
  useEffect(() => {
    try {
      const stored = localStorage.getItem(CONFIG.AUTH_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.token && parsed.user) {
          if (isTokenExpired(parsed.token)) {
            logout();
          } else {
            setToken(parsed.token);
            setUser(parsed.user);
          }
        }
      }
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  // Listen for 401 session-expired event
  useEffect(() => {
    const handleExpired = () => {
      logout();
    };
    window.addEventListener('patienttriage:session-expired', handleExpired);
    return () => window.removeEventListener('patienttriage:session-expired', handleExpired);
  }, [logout]);

  const login = async (role: Role) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(role);
      setToken(res.access_token);
      setUser(res.user);
      localStorage.setItem(
        CONFIG.AUTH_STORAGE_KEY,
        JSON.stringify({ token: res.access_token, user: res.user })
      );
    } finally {
      setIsLoading(false);
    }
  };

  const hasRole = (...roles: Role[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
