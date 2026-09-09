import { createContext, useContext, useState, ReactNode, useCallback } from "react";

interface Tokens {
  access: string;
  refresh: string;
}

const STORAGE_KEY = "nagrik-setu-tokens";

// localStorage is fine here (this is a real deployed app, not a Claude
// artifact sandbox) but note the tradeoff: an httpOnly cookie set by the
// backend is the more XSS-resistant option if you're hardening this later.
function readStoredTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

function writeStoredTokens(tokens: Tokens | null) {
  if (tokens) localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  else localStorage.removeItem(STORAGE_KEY);
}

interface AuthContextValue {
  isAuthenticated: boolean;
  accessToken: string | null;
  login: (tokens: Tokens) => void;
  logout: () => void;
  setAccessToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<Tokens | null>(() => readStoredTokens());

  const login = useCallback((newTokens: Tokens) => {
    writeStoredTokens(newTokens);
    setTokens(newTokens);
  }, []);

  const logout = useCallback(() => {
    writeStoredTokens(null);
    setTokens(null);
  }, []);

  const setAccessToken = useCallback((token: string) => {
    setTokens((prev) => {
      const next = prev ? { ...prev, access: token } : null;
      writeStoredTokens(next);
      return next;
    });
  }, []);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated: !!tokens, accessToken: tokens?.access ?? null, login, logout, setAccessToken }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export function getStoredRefreshToken(): string | null {
  return readStoredTokens()?.refresh ?? null;
}

export function getStoredAccessToken(): string | null {
  return readStoredTokens()?.access ?? null;
}

export function updateStoredAccessToken(token: string) {
  const current = readStoredTokens();
  if (current) writeStoredTokens({ ...current, access: token });
}

export function clearStoredTokens() {
  writeStoredTokens(null);
}
