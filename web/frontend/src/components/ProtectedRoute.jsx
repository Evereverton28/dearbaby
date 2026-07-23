import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';
import { Loading } from './Bits';

/* Gate a route in the client. This is ROUTING, not security — every request
   the page makes is independently authorised by the server. */
export default function ProtectedRoute({ children, capability }) {
  const { user, loading, can } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (capability && !can(capability)) return <Navigate to="/app" replace />;
  return children;
}
