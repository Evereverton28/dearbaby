import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api, { setTokens, getAccessToken } from './api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  const applySession = useCallback((data) => {
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    setPermissions(data.permissions || []);
    return data;
  }, []);

  const signOut = useCallback(() => {
    setTokens(null, null); setUser(null); setPermissions([]);
  }, []);

  useEffect(() => {
    /* The api layer fires this when a refresh fails — e.g. an admin
       deactivated this account mid-session. */
    const onSignedOut = () => signOut();
    window.addEventListener('db:signed-out', onSignedOut);
    return () => window.removeEventListener('db:signed-out', onSignedOut);
  }, [signOut]);

  useEffect(() => {
    if (!getAccessToken()) { setLoading(false); return; }
    api.get('/auth/me')
      .then(({ data }) => { setUser(data.user); setPermissions(data.permissions || []); })
      .catch(() => signOut())
      .finally(() => setLoading(false));
  }, [signOut]);

  const value = {
    user, permissions, loading, signOut,
    isPremiumGate: (err) => err?.response?.status === 402,
    signIn: (email, password) =>
      api.post('/auth/login', { email, password }).then((r) => applySession(r.data)),
    signUp: (payload) =>
      api.post('/auth/register', payload).then((r) => applySession(r.data)),
    /* UX only — the server re-checks on every request. */
    can: (capability) => permissions.includes('*') || permissions.includes(capability),
    refreshUser: () => api.get('/auth/me').then(({ data }) => {
      setUser(data.user); setPermissions(data.permissions || []);
    }),
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
