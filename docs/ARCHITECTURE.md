# DearBaby — Architecture & Technical Decisions

This document explains *what to build with and why*. Every choice here is made for a
small team (1–4 people) shipping a real product on a realistic budget, with M-PESA as a
first-class payment method (Kenya market) and medical/child data handled responsibly.

---

## 1. Recommended stack

| Layer | Choice | Why this and not the obvious alternative |
|---|---|---|
| **Mobile app** | **React Native + Expo (TypeScript)** | One codebase → iOS + Android. Expo gives you OTA updates, push notifications, camera, and secure storage out of the box. Flutter is also excellent, but React Native keeps you in the JS/TS ecosystem, which has the deepest hiring pool and library support for the community + payment SDKs you need. |
| **Backend API** | **FastAPI (Python 3.11+)** | You already work in Python. FastAPI is async, fast, auto-generates OpenAPI docs (which the mobile app and admin dashboard both consume), and has first-class typing via Pydantic. |
| **Database** | **PostgreSQL 15** | Relational data (users, subscriptions, milestones, community) with strong integrity guarantees. Managed Postgres is cheap and scales far past your first 100k users. |
| **Object storage** | **Cloudflare R2** (or AWS S3) | Photos/videos do **not** go in the database. R2 has no egress fees — a big deal when families download and share media constantly. |
| **Auth** | **Custom JWT in FastAPI** + social login (Google/Apple) | Full control, no per-MAU vendor fee. See `docs/API.md` for the token model. If you'd rather not run auth yourself, Supabase Auth or Clerk are drop-in alternatives. |
| **Admin dashboard** | **Next.js (React) + shadcn/ui** | Web app, shares TypeScript types with the mobile app. Talks to the same FastAPI backend. |
| **Push notifications** | **Expo Push** → FCM (Android) + APNs (iOS) | Expo abstracts both stores behind one API. |
| **Background jobs** | **Celery + Redis** (or `arq`) | Reminders, print-book PDF generation, media transcoding, email — all async. |
| **Payments** | **Stripe** (cards, Google Pay, Apple Pay) + **Safaricom Daraja API** (M-PESA STK Push) | Stripe covers global cards and *is* the Apple/Google Pay rails. M-PESA needs a separate direct integration — see §4. |
| **Hosting** | Backend on **Railway / Render / Fly.io** to start; move to a managed K8s or ECS only when traffic demands it | Don't over-provision infrastructure for users you don't have yet. |

---

## 2. System diagram (logical)

```
                    ┌──────────────────┐        ┌──────────────────┐
                    │  Mobile App      │        │  Admin Dashboard │
                    │ (React Native)   │        │   (Next.js)      │
                    └────────┬─────────┘        └────────┬─────────┘
                             │  HTTPS / JSON (OpenAPI)    │
                             └────────────┬──────────────┘
                                          ▼
                              ┌───────────────────────┐
                              │   FastAPI backend      │
                              │  (auth, domain, admin) │
                              └───┬───────┬────────┬───┘
             ┌────────────────────┘       │        └───────────────────┐
             ▼                            ▼                            ▼
   ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
   │  PostgreSQL      │        │  Redis + Celery  │        │  Object storage  │
   │  (all records)   │        │  (jobs/reminders)│        │  (R2 / S3 media) │
   └──────────────────┘        └────────┬─────────┘        └──────────────────┘
                                         │
                     ┌───────────────────┼────────────────────┐
                     ▼                   ▼                    ▼
              ┌────────────┐     ┌──────────────┐     ┌──────────────┐
              │ Stripe     │     │ M-PESA Daraja│     │ Expo Push /  │
              │ (cards/pay)│     │ (STK Push)   │     │ FCM + APNs   │
              └────────────┘     └──────────────┘     └──────────────┘
```

The mobile app **never** talks to Stripe/M-PESA/storage directly for anything sensitive.
It requests a signed URL or a payment intent from the backend, and the backend is the
only party holding secret keys.

---

## 3. Offline support & sync (this is the hard part — plan for it early)

Families will journal on planes, in hospitals with bad signal, in rural areas. Offline is
not a nice-to-have here.

**Approach: local-first with a sync queue.**

- The app keeps a local **SQLite** database (via `expo-sqlite` or WatermelonDB).
- All writes go to local SQLite first and render instantly.
- A **sync queue** table records each pending change with a client-generated UUID and a
  `updated_at` timestamp.
- When connectivity returns, the queue flushes to the backend. The backend uses
  **last-write-wins by `updated_at`** for simple records, and append-only semantics for
  things that can't conflict (new journal entries, new photos).
- Media uploads: the local file is saved immediately; the upload to R2 happens in the
  background and the record's `media_status` moves `pending → uploaded`.

**Every mutable table therefore carries:** `id (uuid)`, `updated_at`, `deleted_at` (soft
delete, so a delete on one device propagates instead of a row silently reappearing).

---

## 4. Payments — the part people underestimate

**Subscriptions (30-day trial, monthly, annual):**
- Stripe **Billing** manages the subscription lifecycle, proration, and card/Apple
  Pay/Google Pay. Use Stripe Checkout or the Payment Sheet in the app.
- **App Store / Play Store rule:** if you sell digital subscriptions inside the iOS/Android
  apps, Apple and Google generally require their *in-app purchase* systems (and take
  15–30%). Selling premium features through Stripe/M-PESA directly can get the app
  rejected. Realistic options: (a) use RevenueCat to wrap Apple/Google IAP for in-app
  upgrades, and (b) offer M-PESA/Stripe on your **website** for subscriptions purchased
  outside the app. Decide this before you build the paywall — it shapes the flow.

**M-PESA (Daraja API):**
- Flow is **STK Push**: backend calls Daraja `/stkpush`, the user gets a PIN prompt on
  their phone, and Safaricom calls your **callback URL** with the result.
- You need: a Daraja app (Consumer Key/Secret), a Shortcode (Paybill/Till), and a passkey.
- M-PESA is **asynchronous and callback-driven** — never assume payment succeeded from the
  initial API response; wait for the confirmation callback and reconcile.
- Because M-PESA has no native recurring billing, "subscriptions" via M-PESA are really
  *renewal reminders* + a fresh STK Push each cycle.

---

## 5. Security & compliance (non-negotiable for a baby/medical app)

- **Ultrasounds, medical reports, and children's data** are sensitive. Encrypt media at
  rest (R2/S3 server-side encryption) and in transit (TLS everywhere).
- Passwords hashed with **bcrypt/argon2**, never reversible.
- Signed, expiring URLs for every media fetch — no public buckets.
- **GDPR/consent + Kenya's Data Protection Act (2019):** you must support data export and
  full account deletion (both are in the feature list — good). Register with the ODPC if
  operating in Kenya at scale.
- Community: store moderation actions in an audit log; support report → review → action.
- Children can't consent — the *parent* is the account holder and data controller for the
  child's profile. Make that explicit in your terms.

---

## 6. Repository layout (monorepo recommended)

```
dearbaby/
├── backend/        # FastAPI — API, auth, jobs, admin endpoints
├── mobile/         # React Native + Expo app
├── admin/          # Next.js admin dashboard  (build in a later phase)
├── docs/           # this folder
└── infra/          # deploy config, docker-compose, IaC  (later)
```

Shared API types: generate a TypeScript client for `mobile/` and `admin/` directly from
FastAPI's OpenAPI schema (`openapi-typescript`), so the frontend and backend never drift.

---

## 7. What to build first (see ROADMAP.md for the full plan)

The single most important discipline on a project this size is **not building all 12
features at once.** Ship a spine users can love, then add rooms onto the house. The
foundation in this repo — auth, schema, media, one journey feature — is that spine.
