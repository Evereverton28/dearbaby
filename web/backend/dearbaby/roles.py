"""
Single source of truth for roles, permissions, and the management hierarchy.

Two maps, not one (see architecture brief §3):

  PERMISSIONS tells you *what a role can do*.
  HIERARCHY   tells you *whose accounts a role may act on*.

The permission opens the door; the hierarchy decides how far in you get.
An admin holds the "users" permission, but the hierarchy narrows it to
moderators only — they cannot touch another admin or a super_admin.

This file is mirrored in the frontend at src/config/roles.js. That mirror is
UX ONLY (hiding menu items, picking a landing page). Enforcement lives here.
"""

# --- role constants -----------------------------------------------------
PARENT = "parent"            # the end user: an expectant parent / family member
MODERATOR = "moderator"      # community moderation only
ADMIN = "admin"              # runs the product day to day
SUPER_ADMIN = "super_admin"  # everything, incl. system settings

ALL_ROLES = (PARENT, MODERATOR, ADMIN, SUPER_ADMIN)

# The role assigned by the public signup door. Hardcoded server-side and
# never read from the request payload.
DEFAULT_PUBLIC_ROLE = PARENT

# --- (a) permission map -------------------------------------------------
# Capabilities in the admin area. "*" means everything.
PERMISSIONS = {
    SUPER_ADMIN: {"*"},
    ADMIN: {
        "users",          # manage accounts (narrowed further by HIERARCHY)
        "subscriptions",
        "moderation",
        "analytics",
        "announcements",
        "recipes",
        "content",        # pregnancy week content library
    },
    MODERATOR: {
        "moderation",     # review reports, hide/remove posts
        "content",
    },
    PARENT: set(),        # no admin-area capability at all
}

# --- (b) hierarchy map --------------------------------------------------
# Which roles each role may create / edit / deactivate / delete.
# Note SUPER_ADMIN is absent from every value list: the highest role is
# never manageable through the panel (seed script or invite endpoint only).
HIERARCHY = {
    SUPER_ADMIN: {ADMIN, MODERATOR},
    ADMIN: {MODERATOR},
    MODERATOR: set(),
    PARENT: set(),
}

# --- landing pages ------------------------------------------------------
# Where the client sends a user after login, by role.
LANDING = {
    PARENT: "/app",              # the storefront equivalent: their memory book
    MODERATOR: "/admin/moderation",
    ADMIN: "/admin",
    SUPER_ADMIN: "/admin",
}


def has_permission(role: str, capability: str) -> bool:
    """True if `role` holds `capability`."""
    granted = PERMISSIONS.get(role, set())
    return "*" in granted or capability in granted


def can_manage(actor_role: str, target_role: str) -> bool:
    """True if `actor_role` may create/edit/deactivate an account of `target_role`."""
    return target_role in HIERARCHY.get(actor_role, set())


def manageable_roles(actor_role: str) -> list:
    """Roles this actor is allowed to assign — drives the role dropdown."""
    return sorted(HIERARCHY.get(actor_role, set()))


def is_admin_area(role: str) -> bool:
    return bool(PERMISSIONS.get(role, set()))
