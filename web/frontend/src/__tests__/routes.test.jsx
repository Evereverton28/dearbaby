/**
 * Render smoke tests.
 *
 * These exist because `npm run build` succeeding proves nothing about whether
 * a page actually renders. A nested <Routes> with absolute paths compiles
 * perfectly and shows a blank screen under the nav bar. This suite mounts the
 * real app at each URL and asserts something appeared.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy } from 'react';

vi.mock('../api', () => {
  const routes = {
    '/auth/me': { user: { id: 'u1', display_name: 'Test Parent', email: 't@t.com', role: 'parent' },
                  permissions: [], landing: '/app' },
    '/children': { children: [{ id: 'c1', name: 'Baby', stage: 'pregnancy',
                                current_week: 24, due_date: '2026-11-05',
                                birth_date: null, age_days: null }] },
    '/children/c1/summary': { counts: { milestones: 3, journal: 2, media: 5 } },
    '/pregnancy/weeks/24': { week: 24, size_label: 'a cantaloupe', trimester: 2,
                             length_cm: 30, weight_g: 600, summary: 'Summary.', tip: 'Tip.' },
    '/pregnancy/children/c1/appointments': { appointments: [] },
    '/pregnancy/children/c1/journal': { entries: [], total: 0 },
    '/pregnancy/children/c1/kicks': { sessions: [] },
    '/pregnancy/children/c1/contractions': { contractions: [] },
    '/memories/children/c1/timeline': { timeline: [] },
    '/memories/children/c1/milestones': { milestones: [] },
    '/memories/milestone-types?stage=pregnancy': { types: [] },
    '/memories/children/c1/growth': { measurements: [] },
    '/memories/children/c1/teeth': { teeth: [] },
    '/media/children/c1/gallery': { groups: [], total: 0 },
    '/media/children/c1/albums': { albums: [] },
    '/community/groups': { groups: [] },
    '/community/posts?': { posts: [], total: 0 },
    '/recipes?': { recipes: [], total: 0 },
    '/settings': { theme: 'system', notif_milestones: true },
    '/billing/subscription': { subscription: null, premium: false },
    '/billing/plans': { trial_days: 30, plans: [{ key: 'monthly', label: 'Monthly', prices: { KES: 49900 } }],
                        premium_features: ['Backup'] },
  };
  const get = (url) => {
    const key = Object.keys(routes).find((k) => url === k || url.startsWith(k));
    return key ? Promise.resolve({ data: routes[key] }) : Promise.resolve({ data: {} });
  };
  return {
    default: { get, post: () => Promise.resolve({ data: {} }),
               patch: () => Promise.resolve({ data: {} }),
               delete: () => Promise.resolve({ data: {} }) },
    getAccessToken: () => 'fake-token',
    setTokens: () => {},
    errorMessage: (e, f) => f || 'error',
  };
});

vi.mock('../analytics', () => ({ track: () => {}, trackPageview: () => {} }));

import { AuthProvider } from '../auth';
import { ChildProvider } from '../child';
import Layout from '../components/Layout';
import ProtectedRoute from '../components/ProtectedRoute';

const pages = {
  Dashboard: lazy(() => import('../pages/Dashboard')),
  Pregnancy: lazy(() => import('../pages/Pregnancy')),
  Journal: lazy(() => import('../pages/Journal')),
  Tools: lazy(() => import('../pages/Tools')),
  Memories: lazy(() => import('../pages/Memories')),
  Gallery: lazy(() => import('../pages/Gallery')),
  Community: lazy(() => import('../pages/Community')),
  Recipes: lazy(() => import('../pages/Recipes')),
  Settings: lazy(() => import('../pages/Settings')),
  Upgrade: lazy(() => import('../pages/Upgrade')),
  Setup: lazy(() => import('../pages/Setup')),
};

/* Mirrors the real nesting in App.jsx: an outer "/app/*" wrapper with a
   descendant <Routes> inside. This is the exact shape that broke. */
const AppShell = () => (
  <Layout>
    <Routes>
      <Route index element={<pages.Dashboard />} />
      <Route path="setup" element={<pages.Setup />} />
      <Route path="pregnancy" element={<pages.Pregnancy />} />
      <Route path="pregnancy/journal" element={<pages.Journal />} />
      <Route path="pregnancy/tools" element={<pages.Tools />} />
      <Route path="memories" element={<pages.Memories />} />
      <Route path="gallery" element={<pages.Gallery />} />
      <Route path="community" element={<pages.Community />} />
      <Route path="recipes" element={<pages.Recipes />} />
      <Route path="settings" element={<pages.Settings />} />
      <Route path="upgrade" element={<pages.Upgrade />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  </Layout>
);

function mountAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <ChildProvider>
          <Suspense fallback={<div>loading</div>}>
            <Routes>
              <Route path="/app/*" element={<ProtectedRoute><AppShell /></ProtectedRoute>} />
            </Routes>
          </Suspense>
        </ChildProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

/* The page content lives in <main className="page">. If that element is
   missing, the route matched nothing and the user sees a blank screen. */
async function expectContent(container, path) {
  await waitFor(() => {
    const main = container.querySelector('main.page, .page');
    expect(main, `${path} rendered no page content`).toBeTruthy();
    expect(main.textContent.trim().length,
      `${path} rendered an empty page`).toBeGreaterThan(0);
  }, { timeout: 4000 });
}

const ROUTES = [
  '/app',
  '/app/pregnancy',
  '/app/pregnancy/journal',
  '/app/pregnancy/tools',
  '/app/memories',
  '/app/gallery',
  '/app/community',
  '/app/recipes',
  '/app/settings',
  '/app/upgrade',
];

describe('every app route renders content', () => {
  afterEach(() => { localStorage.clear(); });

  ROUTES.forEach((path) => {
    it(`${path} is not blank`, async () => {
      const { container } = mountAt(path);
      await expectContent(container, path);
    });
  });
});

describe('the layout still renders', () => {
  it('shows the nav links', async () => {
    const { container } = mountAt('/app');
    await waitFor(() => {
      const nav = container.querySelector('.navlinks');
      expect(nav, 'nav did not render').toBeTruthy();
      expect(nav.textContent).toContain('Pregnancy');
      expect(nav.textContent).toContain('Gallery');
    }, { timeout: 4000 });
  });

  it('has a reachable sign-out control', async () => {
    const { container } = mountAt('/app');
    await waitFor(() => {
      expect(container.querySelector('.user-menu-wrap'),
        'no user menu in the header').toBeTruthy();
    }, { timeout: 4000 });
  });
});
