# DearBaby — Build Roadmap

The goal is to ship something families love *early*, then grow. Building all 12
feature areas before launch is the surest way to run out of time and money. Each
phase below is releasable on its own.

## Phase 0 — Foundation *(this repo covers the start of it)*
- ✅ Architecture & stack decisions (`docs/ARCHITECTURE.md`)
- ✅ Database schema for all features (`backend/schema.sql`)
- ✅ API map (`docs/API.md`)
- ✅ Runnable auth core: signup / login / social stub / refresh / me
- ⬜ Media upload pipeline (signed URLs → R2/S3 → thumbnails)
- ⬜ Alembic migrations; swap SQLite → Postgres
- ⬜ Mobile app shell (Expo, navigation, design system, auth screens)

**Milestone:** a user can register, log in, and see an empty home.

## Phase 1 — The memory spine (the reason people install)
- Children/pregnancy setup, weekly pregnancy tracker
- Journal entries with photos
- Milestones + timeline view
- Photo/video gallery with albums and cloud backup
- Offline-first local SQLite + sync queue

**Milestone:** a pregnant user documents their journey end to end. Soft-launch.

## Phase 2 — Retention & delight
- Baby memory book (birth record, teeth, growth charts)
- Kick counter & contraction timer
- Notifications/reminders (pregnancy weeks, milestones, vaccinations, birthdays)
- Sharing selected memories with family

**Milestone:** daily-use habit forms; families invite each other → organic growth.

## Phase 3 — Monetization
- Subscription (30-day trial, monthly, annual)
- Payments: Stripe (cards/Apple Pay/Google Pay) + M-PESA STK Push
- Paywall around premium features
- Settings: dark mode, export, delete account, privacy controls

**Milestone:** revenue begins; unit economics become measurable.

## Phase 4 — Community & content
- Groups, discussions, Q&A, likes, comments, follows
- Moderation tools + reporting
- Recipes (weaning/baby food, search, favorites)

**Milestone:** network effects and content keep users engaged between milestones.

## Phase 5 — Creation & print
- Digital scrapbook (drag-drop layouts, stickers, themes, fonts, templates)
- Printable books → PDF render → order fulfilment

**Milestone:** high-margin physical product; strong emotional/gift use case.

## Phase 6 — Admin & scale
- Admin dashboard (users, subscriptions, moderation, analytics, announcements)
- Observability, backups, load testing, cost tuning

---

## Realistic effort (small team)
| Phase | Rough duration |
|---|---|
| 0 Foundation | 3–5 weeks |
| 1 Memory spine | 6–8 weeks |
| 2 Retention | 4–6 weeks |
| 3 Monetization | 4–6 weeks |
| 4 Community + recipes | 5–7 weeks |
| 5 Scrapbook + print | 6–8 weeks |
| 6 Admin + scale | 4–6 weeks |

Parallelize where you have people; the ordering of *value* stays the same.
Don't let Phase 5's shiny scrapbook jump the queue ahead of the memory spine —
it's the spine that earns the install.
