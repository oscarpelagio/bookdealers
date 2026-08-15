import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import * as authApi from '@/api/auth';
import { setAuthAccessToken, setUnauthorizedHandler } from '@/api/client';
import type { AuthTokens, AuthUser, RegisterRequest, RegisterResponse } from '@/api/types';
import { tokenStorage } from '@/lib/token-storage';

const ACCESS_KEY = 'bookdealers.access_token';
const REFRESH_KEY = 'bookdealers.refresh_token';
const USER_KEY = 'bookdealers.user';

export type AuthStatus = 'restoring' | 'signedIn' | 'signedOut';

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  signIn: (email: string, password: string, deviceId?: string | null) => Promise<AuthUser>;
  signUp: (payload: RegisterRequest) => Promise<RegisterResponse>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('restoring');
  const [user, setUser] = useState<AuthUser | null>(null);
  const tokensRef = useRef<AuthTokens | null>(null);
  const refreshing = useRef<boolean>(false);

  const persistTokens = useCallback(async (tokens: AuthTokens) => {
    tokensRef.current = tokens;
    await tokenStorage.setItem(ACCESS_KEY, tokens.access_token);
    await tokenStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  }, []);

  const refreshTokens = useCallback(async (): Promise<AuthTokens | null> => {
    const refreshToken = tokensRef.current?.refresh_token;
    if (!refreshToken) return null;
    const tokens = await authApi.refresh(refreshToken);
    await persistTokens(tokens);
    return tokens;
  }, [persistTokens]);

  const signOut = useCallback(async () => {
    const refreshToken = tokensRef.current?.refresh_token;
    if (refreshToken) {
      authApi.logout(refreshToken).catch(() => {});
    }
    tokensRef.current = null;
    await tokenStorage.removeItem(ACCESS_KEY);
    await tokenStorage.removeItem(REFRESH_KEY);
    await tokenStorage.removeItem(USER_KEY);
    setAuthAccessToken(null);
    setUser(null);
    setStatus('signedOut');
  }, []);

  const handleUnauthorized = useCallback(async (): Promise<boolean> => {
    if (refreshing.current) return false;
    refreshing.current = true;
    try {
      const tokens = await refreshTokens();
      if (tokens) {
        setAuthAccessToken(tokens.access_token);
        return true;
      }
    } catch {
      await signOut();
    } finally {
      refreshing.current = false;
    }
    return false;
  }, [refreshTokens, signOut]);

  const signIn = useCallback(async (email: string, password: string, deviceId?: string | null) => {
    const tokens = await authApi.login(email, password, deviceId);
    await persistTokens(tokens);
    setAuthAccessToken(tokens.access_token);
    const currentUser = await authApi.me();
    await tokenStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    setUser(currentUser);
    setStatus('signedIn');
    return currentUser;
  }, [persistTokens]);

  const signUp = useCallback(async (payload: RegisterRequest) => {
    return authApi.register(payload);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(handleUnauthorized);

    (async () => {
      try {
        const [accessToken, refreshToken] = await Promise.all([
          tokenStorage.getItem(ACCESS_KEY),
          tokenStorage.getItem(REFRESH_KEY),
        ]);

        if (accessToken && refreshToken) {
          tokensRef.current = {
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: 'bearer',
            access_token_expires_in: 0,
            refresh_token_expires_in: 0,
            expires_at: '',
          };
          setAuthAccessToken(accessToken);

          try {
            // If the access token is expired, the client refreshes automatically
            // via the 401 handler and retries before throwing.
            const currentUser = await authApi.me();
            await tokenStorage.setItem(USER_KEY, JSON.stringify(currentUser));
            setUser(currentUser);
            setStatus('signedIn');
            return;
          } catch {
            await signOut();
            return;
          }
        }

        setStatus('signedOut');
      } catch {
        setStatus('signedOut');
      }
    })();

    return () => setUnauthorizedHandler(null);
  }, [handleUnauthorized, signOut]);

  const value = useMemo(
    () => ({ status, user, signIn, signUp, signOut }),
    [status, user, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}