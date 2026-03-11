"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { User } from "@/lib/api";
import { getSession, logout as logoutRequest } from "@/lib/auth";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: string | null;
  refreshSession: () => Promise<User | null>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasBootstrapped = useRef(false);

  const refreshSession = useCallback(async () => {
    try {
      const session = await getSession();
      setUser(session);
      setError(null);
      return session;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load session";
      setUser(null);
      setError(message);
      return null;
    }
  }, []);

  useEffect(() => {
    if (hasBootstrapped.current) {
      return;
    }

    hasBootstrapped.current = true;

    const bootstrap = async () => {
      setLoading(true);
      await refreshSession();
      setLoading(false);
    };

    void bootstrap();
  }, [refreshSession]);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, refreshSession, logout }),
    [user, loading, error, refreshSession, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
