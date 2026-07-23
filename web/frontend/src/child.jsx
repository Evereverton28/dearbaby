/* Which child is being viewed. Every memory feature needs it, so it lives in
   one context rather than being threaded through every page. */
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from './api';
import { useAuth } from './auth';

const ChildContext = createContext(null);
export const useChild = () => useContext(ChildContext);

export function ChildProvider({ children }) {
  const { user } = useAuth();
  const [list, setList] = useState([]);
  const [activeId, setActiveId] = useState(localStorage.getItem('db_child') || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!user) { setList([]); setLoading(false); return; }
    setError(null);
    try {
      const { data } = await api.get('/children');
      setList(data.children);
      setActiveId((cur) => {
        const stillThere = data.children.some((c) => c.id === cur);
        return stillThere ? cur : (data.children[0]?.id || null);
      });
    } catch (err) {
      console.error('Failed to load children:', err);
      setError('Could not connect to the server. Is the backend running on port 5000?');
      setList([]);
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (activeId) localStorage.setItem('db_child', activeId);
  }, [activeId]);

  const active = list.find((c) => c.id === activeId) || null;
  return (
    <ChildContext.Provider value={{ list, active, activeId, setActiveId, reload: load, loading, error }}>
      {children}
    </ChildContext.Provider>
  );
}
