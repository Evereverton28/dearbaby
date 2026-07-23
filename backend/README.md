# DearBaby Backend (FastAPI)

Runnable auth core. Extend by adding routers under `app/api/` and models under
`app/models/`, following the pattern in `auth.py` / `user.py`.

## Run locally
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs for interactive API docs.

## What's here
- `app/core/config.py`   — settings (SQLite in dev, point `database_url` at Postgres in prod)
- `app/core/security.py` — bcrypt hashing + JWT access/refresh tokens
- `app/core/db.py`       — engine/session; `init_db()` for dev (use Alembic in prod)
- `app/models/`          — SQLModel tables (User, Child)
- `app/api/auth.py`      — signup, login, social stub, refresh, password-reset, me
- `app/api/deps.py`      — `get_current_user`, `require_admin`
- `schema.sql`           — full PostgreSQL schema for ALL 12 feature areas

## Verified working
signup → login → authenticated `/me`; duplicate signup → 409; bad login → 401;
unauthenticated `/me` → 401.

## Next steps
1. `alembic init` and generate migrations from `schema.sql` against Postgres.
2. Implement Google/Apple token verification in `/auth/social`.
3. Add the media upload-URL endpoint (signed R2/S3 URLs).
4. Build routers for children, milestones, gallery (Phase 1).
