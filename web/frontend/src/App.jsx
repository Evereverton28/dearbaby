import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';
import { ChildProvider } from './child';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { Loading } from './components/Bits';
import { trackPageview } from './analytics';
import { watchSystemTheme } from './theme';

/* Route-level code splitting: the initial bundle stays small and heavy
   dependencies (recharts on the admin dashboard) only download for the
   users who actually open those screens. */
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Setup = lazy(() => import('./pages/Setup'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Pregnancy = lazy(() => import('./pages/Pregnancy'));
const Journal = lazy(() => import('./pages/Journal'));
const Tools = lazy(() => import('./pages/Tools'));
const Memories = lazy(() => import('./pages/Memories'));
const Gallery = lazy(() => import('./pages/Gallery'));
const Community = lazy(() => import('./pages/Community'));
const PostDetail = lazy(() => import('./pages/PostDetail'));
const Recipes = lazy(() => import('./pages/Recipes'));
const Settings = lazy(() => import('./pages/Settings'));
const Upgrade = lazy(() => import('./pages/Upgrade'));

const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'));
const Overview = lazy(() => import('./pages/admin/Overview'));
const Users = lazy(() => import('./pages/admin/Users'));
const ModerationPage = lazy(() => import('./pages/admin/Moderation'));
const SubscriptionsPage = lazy(() => import('./pages/admin/Subscriptions'));
const AnnouncementsPage = lazy(() => import('./pages/admin/Announcements'));

function Analytics() {
  const location = useLocation();
  useEffect(() => { trackPageview(location.pathname); }, [location.pathname]);
  return null;
}

/* Send signed-in users away from the marketing pages. */
function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  return user ? <Navigate to="/app" replace /> : children;
}

/* NOTE ON NESTED ROUTES.
   These sit inside the parent route <Route path="/app/*">, so React Router
   has already consumed "/app" before it gets here. Paths below MUST be
   relative — an absolute "/app/gallery" would be matched against the
   leftover "gallery" and never hit, rendering a blank page under the nav. */
const App = () => (
  <Layout>
    <Routes>
      <Route index element={<Dashboard />} />
      <Route path="setup" element={<Setup />} />
      <Route path="pregnancy" element={<Pregnancy />} />
      <Route path="pregnancy/journal" element={<Journal />} />
      <Route path="pregnancy/tools" element={<Tools />} />
      <Route path="memories" element={<Memories />} />
      <Route path="gallery" element={<Gallery />} />
      <Route path="community" element={<Community />} />
      <Route path="community/:id" element={<PostDetail />} />
      <Route path="recipes" element={<Recipes />} />
      <Route path="settings" element={<Settings />} />
      <Route path="upgrade" element={<Upgrade />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  </Layout>
);

const Admin = () => (
  <AdminLayout>
    <Routes>
      <Route index element={<Overview />} />
      <Route path="users" element={
        <ProtectedRoute capability="users"><Users /></ProtectedRoute>} />
      <Route path="moderation" element={
        <ProtectedRoute capability="moderation"><ModerationPage /></ProtectedRoute>} />
      <Route path="subscriptions" element={
        <ProtectedRoute capability="subscriptions"><SubscriptionsPage /></ProtectedRoute>} />
      <Route path="announcements" element={
        <ProtectedRoute capability="announcements"><AnnouncementsPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  </AdminLayout>
);

export default function Root() {
  useEffect(() => watchSystemTheme(), []);

  return (
    <BrowserRouter>
      <AuthProvider>
        <ChildProvider>
          <Analytics />
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/" element={<PublicOnly><Landing /></PublicOnly>} />
              <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
              <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
              <Route path="/app/*" element={
                <ProtectedRoute><App /></ProtectedRoute>} />
              <Route path="/admin/*" element={
                <ProtectedRoute capability="moderation"><Admin /></ProtectedRoute>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ChildProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
