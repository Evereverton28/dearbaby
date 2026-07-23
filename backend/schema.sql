-- =============================================================================
-- DearBaby — PostgreSQL schema (v1)
-- Covers all 12 feature areas. Designed for offline sync: every mutable table
-- carries created_at / updated_at / deleted_at (soft delete).
-- Run on PostgreSQL 15+. UUID primary keys via gen_random_uuid() (pgcrypto).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";      -- case-insensitive email

-- Reusable enums -------------------------------------------------------------
CREATE TYPE auth_provider   AS ENUM ('email', 'google', 'apple');
CREATE TYPE user_role       AS ENUM ('user', 'moderator', 'admin');
CREATE TYPE sub_status      AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'expired');
CREATE TYPE sub_plan        AS ENUM ('monthly', 'annual');
CREATE TYPE pay_provider    AS ENUM ('stripe', 'mpesa', 'google_pay', 'apple_pay');
CREATE TYPE pay_status      AS ENUM ('pending', 'succeeded', 'failed', 'refunded');
CREATE TYPE media_kind      AS ENUM ('photo', 'video', 'scan', 'document');
CREATE TYPE media_status    AS ENUM ('pending', 'uploaded', 'processing', 'ready', 'failed');
CREATE TYPE measure_kind    AS ENUM ('height', 'weight', 'head_circumference');
CREATE TYPE reminder_kind   AS ENUM ('milestone', 'pregnancy_week', 'vaccination', 'birthday', 'growth', 'appointment', 'custom');
CREATE TYPE post_status      AS ENUM ('visible', 'hidden', 'removed', 'pending_review');
CREATE TYPE report_status   AS ENUM ('open', 'reviewing', 'actioned', 'dismissed');

-- =============================================================================
-- 1. AUTH & USER PROFILE
-- =============================================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT UNIQUE NOT NULL,
    password_hash   TEXT,                         -- null for social-only accounts
    provider        auth_provider NOT NULL DEFAULT 'email',
    provider_uid    TEXT,                          -- google/apple subject id
    display_name    TEXT NOT NULL,
    avatar_media_id UUID,                          -- FK added after media table
    role            user_role NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    locale          TEXT NOT NULL DEFAULT 'en',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
CREATE UNIQUE INDEX ux_users_provider ON users (provider, provider_uid)
    WHERE provider_uid IS NOT NULL;

-- Refresh tokens / sessions (JWT access tokens stay stateless; refresh is stored)
CREATE TABLE auth_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    device_label    TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE password_resets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Push tokens for notifications
CREATE TABLE device_push_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expo_token  TEXT NOT NULL,
    platform    TEXT NOT NULL,               -- 'ios' | 'android'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, expo_token)
);

-- =============================================================================
-- MEDIA (shared by every feature that stores photos/videos/scans)
-- =============================================================================
CREATE TABLE media_assets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind          media_kind NOT NULL,
    status        media_status NOT NULL DEFAULT 'pending',
    storage_key   TEXT,                       -- R2/S3 object key
    thumb_key     TEXT,
    mime_type     TEXT,
    bytes         BIGINT,
    width         INT,
    height        INT,
    duration_ms   INT,                        -- videos
    captured_at   TIMESTAMPTZ,                -- EXIF date if available
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);
CREATE INDEX ix_media_owner ON media_assets(owner_id) WHERE deleted_at IS NULL;

ALTER TABLE users
    ADD CONSTRAINT fk_users_avatar
    FOREIGN KEY (avatar_media_id) REFERENCES media_assets(id) ON DELETE SET NULL;

-- A "child" (or pregnancy-in-progress) that memories attach to.
-- Multiple caregivers can share one child (partner, grandparent).
CREATE TABLE children (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT,                       -- may be null pre-birth ("Baby")
    due_date        DATE,                       -- pregnancy
    birth_date      DATE,                       -- once born
    sex             TEXT,                       -- 'male'|'female'|'unknown'|null
    cover_media_id  UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

-- Shared access: who can view/edit a child's memory book
CREATE TABLE child_members (
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    can_edit    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (child_id, user_id)
);

-- =============================================================================
-- 2. PREGNANCY JOURNEY
-- =============================================================================
-- Weekly tracker rows are mostly reference content (week 1..42). Store the
-- content library once, and a per-child pointer of "current week".
CREATE TABLE pregnancy_week_content (
    week            INT PRIMARY KEY CHECK (week BETWEEN 1 AND 42),
    baby_size_label TEXT,                       -- "size of a lime"
    baby_length_mm  NUMERIC,
    baby_weight_g   NUMERIC,
    summary         TEXT,
    tips            TEXT
);

CREATE TABLE journal_entries (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    title       TEXT,
    body        TEXT,
    mood        TEXT,
    entry_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

-- Generic link table: attach media to any entity (journal, milestone, entry...)
CREATE TABLE media_links (
    media_id      UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    entity_type   TEXT NOT NULL,               -- 'journal_entry','milestone',...
    entity_id     UUID NOT NULL,
    position      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (media_id, entity_type, entity_id)
);
CREATE INDEX ix_media_links_entity ON media_links(entity_type, entity_id);

CREATE TABLE appointments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    location    TEXT,
    notes       TEXT,
    starts_at   TIMESTAMPTZ NOT NULL,
    reminder_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE kick_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,
    kick_count  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE contraction_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE contractions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES contraction_sessions(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,                    -- duration = ended-started
    -- interval to previous contraction computed at read time
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 3. BABY MEMORY BOOK  (milestones = unified, extensible model)
-- =============================================================================
-- Rather than one table per "first smile / first word", use a typed milestone.
-- Built-in types are seeded; users can add unlimited custom ones.
CREATE TABLE milestone_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT UNIQUE NOT NULL,           -- 'first_smile','first_word'...
    label       TEXT NOT NULL,
    icon        TEXT,
    is_builtin  BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INT NOT NULL DEFAULT 0
);

CREATE TABLE milestones (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id       UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    type_id        UUID REFERENCES milestone_types(id) ON DELETE SET NULL,
    title          TEXT NOT NULL,               -- custom label allowed
    note           TEXT,
    occurred_on    DATE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ
);
CREATE INDEX ix_milestones_child ON milestones(child_id) WHERE deleted_at IS NULL;

-- Birth information (one row per child)
CREATE TABLE birth_records (
    child_id      UUID PRIMARY KEY REFERENCES children(id) ON DELETE CASCADE,
    born_at       TIMESTAMPTZ,
    place         TEXT,
    weight_g      NUMERIC,
    length_cm     NUMERIC,
    head_circ_cm  NUMERIC,
    notes         TEXT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Teeth tracker
CREATE TABLE teeth (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    tooth_code  TEXT NOT NULL,                  -- e.g. 'upper_left_central'
    erupted_on  DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (child_id, tooth_code)
);

-- Height / weight / head-circumference measurements (one table, typed)
CREATE TABLE growth_measurements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    kind        measure_kind NOT NULL,
    value       NUMERIC NOT NULL,               -- cm or kg
    measured_on DATE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
CREATE INDEX ix_growth_child_kind ON growth_measurements(child_id, kind);

-- =============================================================================
-- 4. PHOTO & VIDEO GALLERY  (albums; timeline is derived from captured_at)
-- =============================================================================
CREATE TABLE albums (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    cover_media_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
CREATE TABLE album_media (
    album_id    UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    media_id    UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    position    INT NOT NULL DEFAULT 0,
    PRIMARY KEY (album_id, media_id)
);

-- Sharing selected memories with family (view-only link or invited user)
CREATE TABLE shares (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type   TEXT NOT NULL,               -- 'album','media','milestone'
    entity_id     UUID NOT NULL,
    share_token   TEXT UNIQUE,                 -- for public link shares
    invited_email CITEXT,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 5. DIGITAL SCRAPBOOK & 6. PRINTABLE BOOKS
-- =============================================================================
-- A scrapbook page stores its layout as JSON (positions of media, stickers,
-- text, background). The renderer (app + print pipeline) reads this JSON.
CREATE TABLE scrapbook_pages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id    UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    title       TEXT,
    layout      JSONB NOT NULL DEFAULT '{}',    -- elements, positions, theme
    theme       TEXT,
    position    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE print_books (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id      UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    page_ids      UUID[] NOT NULL DEFAULT '{}', -- ordered scrapbook_pages
    pdf_media_id  UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    status        TEXT NOT NULL DEFAULT 'draft',-- draft|rendering|ready|ordered
    order_ref     TEXT,                          -- print-fulfilment order id
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 7. COMMUNITY
-- =============================================================================
CREATE TABLE groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    is_private  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE group_members (
    group_id    UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'member', -- member|moderator
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE posts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id    UUID REFERENCES groups(id) ON DELETE SET NULL,
    kind        TEXT NOT NULL DEFAULT 'discussion', -- 'discussion'|'question'
    title       TEXT,
    body        TEXT NOT NULL,
    status      post_status NOT NULL DEFAULT 'visible',
    like_count  INT NOT NULL DEFAULT 0,
    reply_count INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
CREATE INDEX ix_posts_group ON posts(group_id) WHERE deleted_at IS NULL;

CREATE TABLE comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id   UUID REFERENCES comments(id) ON DELETE CASCADE, -- threaded
    body        TEXT NOT NULL,
    status      post_status NOT NULL DEFAULT 'visible',
    like_count  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE likes (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,                  -- 'post'|'comment'
    entity_id   UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, entity_type, entity_id)
);

CREATE TABLE follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id),
    CHECK (follower_id <> followee_id)
);

-- Moderation
CREATE TABLE reports (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id   UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    entity_type   TEXT NOT NULL,               -- 'post'|'comment'|'user'
    entity_id     UUID NOT NULL,
    reason        TEXT,
    status        report_status NOT NULL DEFAULT 'open',
    handled_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at   TIMESTAMPTZ
);
CREATE TABLE moderation_actions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    moderator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL,
    entity_id   UUID NOT NULL,
    action      TEXT NOT NULL,                 -- 'hide'|'remove'|'ban'|'warn'
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 8. RECIPES
-- =============================================================================
CREATE TABLE recipes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title        TEXT NOT NULL,
    category     TEXT,                          -- 'weaning'|'baby_food'|...
    min_age_months INT,
    ingredients  JSONB NOT NULL DEFAULT '[]',
    steps        JSONB NOT NULL DEFAULT '[]',
    cover_media_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    search_tsv   TSVECTOR,                      -- full-text search
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_recipes_search ON recipes USING GIN (search_tsv);

CREATE TABLE recipe_favorites (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id   UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, recipe_id)
);

-- =============================================================================
-- 9. NOTIFICATIONS / REMINDERS
-- =============================================================================
CREATE TABLE reminders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    child_id    UUID REFERENCES children(id) ON DELETE CASCADE,
    kind        reminder_kind NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT,
    fire_at     TIMESTAMPTZ NOT NULL,
    recurrence  TEXT,                           -- iCal RRULE or null
    sent_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_reminders_due ON reminders(fire_at) WHERE sent_at IS NULL;

CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT,
    data        JSONB,                          -- deep-link payload
    read_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 10. SUBSCRIPTIONS & PAYMENTS
-- =============================================================================
CREATE TABLE subscriptions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan               sub_plan NOT NULL,
    status             sub_status NOT NULL DEFAULT 'trialing',
    provider           pay_provider NOT NULL,
    provider_sub_id    TEXT,                    -- Stripe subscription id, etc.
    trial_ends_at      TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_subs_user ON subscriptions(user_id);

CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    provider        pay_provider NOT NULL,
    provider_ref    TEXT,                        -- Stripe pi_..., M-PESA receipt
    amount_cents    BIGINT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'KES',
    status          pay_status NOT NULL DEFAULT 'pending',
    raw_payload     JSONB,                       -- callback body for audit
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_payments_user ON payments(user_id);

-- M-PESA needs its own transient state because it is callback-driven
CREATE TABLE mpesa_transactions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checkout_request_id TEXT UNIQUE,             -- returned by STK Push
    merchant_request_id TEXT,
    phone             TEXT NOT NULL,
    amount_cents      BIGINT NOT NULL,
    result_code       INT,                       -- from callback
    result_desc       TEXT,
    mpesa_receipt     TEXT,
    payment_id        UUID REFERENCES payments(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 11. SETTINGS  (per-user preferences)
-- =============================================================================
CREATE TABLE user_settings (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    dark_mode           TEXT NOT NULL DEFAULT 'system', -- 'light'|'dark'|'system'
    notif_milestones    BOOLEAN NOT NULL DEFAULT TRUE,
    notif_pregnancy     BOOLEAN NOT NULL DEFAULT TRUE,
    notif_vaccination   BOOLEAN NOT NULL DEFAULT TRUE,
    notif_birthday      BOOLEAN NOT NULL DEFAULT TRUE,
    notif_growth        BOOLEAN NOT NULL DEFAULT TRUE,
    auto_backup         BOOLEAN NOT NULL DEFAULT TRUE,
    measurement_system  TEXT NOT NULL DEFAULT 'metric',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Data export / delete requests (GDPR / Kenya DPA)
CREATE TABLE data_requests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,                  -- 'export'|'delete'
    status      TEXT NOT NULL DEFAULT 'pending',
    export_media_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- =============================================================================
-- 12. ADMIN — analytics events + announcements
-- =============================================================================
CREATE TABLE announcements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    audience    TEXT NOT NULL DEFAULT 'all',    -- 'all'|'subscribers'|...
    published_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE analytics_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,                  -- 'app_open','milestone_add'...
    props       JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_analytics_name_time ON analytics_events(name, created_at);

-- =============================================================================
-- SYNC SUPPORT — a client cursor so the app can pull "everything since X"
-- =============================================================================
-- Most tables carry updated_at; the app requests /sync?since=<ts> and the
-- backend returns changed rows per table. deleted_at drives tombstone sync.
