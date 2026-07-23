/* =========================================================================
   MIRROR OF THE SERVER ROLE MAP — app/roles.py

   *** THIS IS UX ONLY. IT IS NOT SECURITY. ***

   Its entire job is to hide menu items the user can't use and to pick a
   landing page after login. If someone edits this file in devtools, or skips
   the UI and calls the API directly with a low-privilege token, the SERVER
   still returns 403. That path is covered by the authorization matrix in
   backend/tests/test_authorization.py.

   Keep in sync with app/roles.py. GET /api/admin/roles returns the server's
   maps so you can diff them.
   ========================================================================= */

export const PARENT = 'parent';
export const MODERATOR = 'moderator';
export const ADMIN = 'admin';
export const SUPER_ADMIN = 'super_admin';

export const PERMISSIONS = {
  [SUPER_ADMIN]: ['*'],
  [ADMIN]: ['users', 'subscriptions', 'moderation', 'analytics',
            'announcements', 'recipes', 'content'],
  [MODERATOR]: ['moderation', 'content'],
  [PARENT]: [],
};

export const HIERARCHY = {
  [SUPER_ADMIN]: [ADMIN, MODERATOR],
  [ADMIN]: [MODERATOR],
  [MODERATOR]: [],
  [PARENT]: [],
};

export const LANDING = {
  [PARENT]: '/app',
  [MODERATOR]: '/admin/moderation',
  [ADMIN]: '/admin',
  [SUPER_ADMIN]: '/admin',
};

export function hasPermission(role, capability) {
  const granted = PERMISSIONS[role] || [];
  return granted.includes('*') || granted.includes(capability);
}

export function canManage(actorRole, targetRole) {
  return (HIERARCHY[actorRole] || []).includes(targetRole);
}

/* Landing page after login. If the role can't open the dashboard, send it to
   the first page it CAN open rather than bouncing it into a 403. */
export function landingFor(role) {
  return LANDING[role] || '/app';
}
