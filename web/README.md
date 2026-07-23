# DearBaby — Web App

Web first, mobile after. Built on the patterns in the supplied architecture
brief: Flask app-factory + blueprints, one login for everyone, two signup
doors, two-map RBAC, token-driven theming, self-hosted analytics.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py            # one account per role + 30 days of synthetic traffic
python app.py             # http://localhost:5000
```

Seeded logins (password `ChangeMe!2026`):

| Role | Email | Lands on |
|---|---|---|
| super_admin | owner@dearbaby.app | /admin |
| admin | admin@dearbaby.app | /admin |
| moderator | mod@dearbaby.app | /admin/moderation |
| parent | amara@example.com | /app |

## Tests

```bash
cd backend && python -m pytest tests/ -v      # 18 pass
python frontend/src/styles/contrast_check.py  # WCAG audit, both themes
```

## What's implemented

| Brief section | Status |
|---|---|
| §1 Factory + blueprints, REST split | done — `dearbaby/__init__.py`, one blueprint per domain |
| §2 One login, two signup doors | done — public door hardcodes `parent` |
| §3 Two-map RBAC + hierarchy | done — `dearbaby/roles.py`, `dearbaby/decorators.py` |
| §3 Deactivation at token-validation layer | done — blocklist callback, tested |
| §4 Token theming + dark mode | done — `tokens.css`, one override block |
| §4 Double-duty token split | done — `--accent-text` / `--accent-solid` |
| §4 Pre-paint script | done — blocking, in `<head>` |
| §4 Contrast verified numerically | done — all pairings pass |
| §6 Self-hosted analytics | done — `/api/track` + query-time aggregates |
| §7 Seed data per role | done — `seed.py` |
| §5 Responsive layout | tokens + table-scroll ready; pages pending |
| DearBaby feature modules | **pending — awaiting your feature list** |

## Roles

```
PERMISSIONS          HIERARCHY (who may manage whom)
super_admin : *      super_admin -> admin, moderator
admin       : users, subscriptions,    admin -> moderator
              moderation, analytics,   moderator -> nobody
              announcements, recipes   parent -> nobody
moderator   : moderation, content
parent      : (nothing in admin area)
```

`super_admin` appears in no hierarchy value list — the highest role is
unreachable through the panel by design. Seed script or invite code only.

## Adding a feature module

1. `dearbaby/<domain>/routes.py` with a blueprint
2. Register it in `create_app()`
3. Gate every route with `@permission_required("<capability>")`
4. Add the capability to `PERMISSIONS` in `dearbaby/roles.py` **and** the client mirror
5. Add a row to the matrix in `tests/test_authorization.py`
