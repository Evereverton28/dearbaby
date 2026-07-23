# DearBaby — API Reference

REST over HTTPS, JSON bodies. FastAPI auto-generates interactive docs at `/docs`
(Swagger) and `/redoc`. This file is the human-readable map of the surface area.

## Conventions
- **Auth:** `Authorization: Bearer <access_token>`. Access tokens are short-lived
  (30 min); refresh with `/auth/refresh`.
- **IDs:** UUID strings, client-generatable (for offline creation).
- **Timestamps:** ISO-8601 UTC.
- **Errors:** `{ "detail": "message" }` with the right HTTP status.
- **Pagination:** `?limit=&cursor=` (keyset pagination on `created_at,id`).
- **Sync:** most list endpoints accept `?since=<iso-timestamp>` to return only
  rows changed after that time, including tombstones (rows with `deleted_at`).

Legend: 🔒 auth required · 👑 admin only

---

## Auth  *(implemented in this repo)*
| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Email/password registration → tokens |
| POST | `/auth/login` | Email/password login (form) → tokens |
| POST | `/auth/social` | Google/Apple login (verify provider id_token) |
| POST | `/auth/refresh` | Exchange refresh token for a new pair |
| POST | `/auth/password-reset` | Trigger reset email (always 202) |
| GET | `/auth/me` 🔒 | Current user profile |
| PATCH | `/users/me` 🔒 | Update profile / avatar |

## Children (memory subjects)
| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/children` 🔒 | List / create a child or pregnancy |
| GET/PATCH/DELETE | `/children/{id}` 🔒 | Read / update / soft-delete |
| POST | `/children/{id}/members` 🔒 | Invite a co-parent/family member |

## Pregnancy journey
| Method | Path | Purpose |
|---|---|---|
| GET | `/pregnancy/weeks/{week}` | Weekly tracker content (1–42) |
| GET/POST | `/children/{id}/journal` 🔒 | Journal entries |
| GET/POST | `/children/{id}/appointments` 🔒 | Appointment tracker |
| POST | `/children/{id}/kick-sessions` 🔒 | Start/record kick counter |
| POST | `/children/{id}/contraction-sessions` 🔒 | Contraction timer |

## Baby memory book
| Method | Path | Purpose |
|---|---|---|
| GET | `/milestone-types` | Built-in + custom milestone types |
| GET/POST | `/children/{id}/milestones` 🔒 | Unlimited milestone entries |
| PUT | `/children/{id}/birth-record` 🔒 | Birth information |
| GET/POST | `/children/{id}/teeth` 🔒 | Teeth tracker |
| GET/POST | `/children/{id}/growth` 🔒 | Height/weight/head measurements |
| GET | `/children/{id}/timeline` 🔒 | Merged, date-ordered feed of everything |

## Media, gallery & sharing
| Method | Path | Purpose |
|---|---|---|
| POST | `/media/upload-url` 🔒 | Get a signed URL to upload directly to storage |
| POST | `/media/{id}/complete` 🔒 | Mark upload finished → triggers thumb/transcode |
| GET | `/media/{id}` 🔒 | Signed, expiring download URL |
| GET/POST | `/children/{id}/albums` 🔒 | Albums |
| POST | `/shares` 🔒 | Share album/media/milestone (link or invite) |
| GET | `/shared/{token}` | Public view of a shared item |

## Scrapbook & printable books
| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/children/{id}/scrapbook` 🔒 | Pages (layout JSON) |
| POST | `/print-books` 🔒 | Compile pages into a book |
| POST | `/print-books/{id}/render` 🔒 | Generate print-ready PDF (async job) |
| POST | `/print-books/{id}/order` 🔒 | Send to print-fulfilment partner |

## Community
| Method | Path | Purpose |
|---|---|---|
| GET | `/groups` | List groups |
| POST | `/groups/{id}/join` 🔒 | Join a group |
| GET/POST | `/posts` 🔒 | Feed / create discussion or question |
| GET/POST | `/posts/{id}/comments` 🔒 | Threaded comments |
| POST | `/likes` / DELETE | Like / unlike a post or comment |
| POST | `/follows/{user_id}` 🔒 | Follow a user |
| POST | `/reports` 🔒 | Report content |

## Recipes
| Method | Path | Purpose |
|---|---|---|
| GET | `/recipes?q=&category=&min_age=` | Search recipes |
| GET | `/recipes/{id}` | Recipe detail |
| POST/DELETE | `/recipes/{id}/favorite` 🔒 | Save / unsave |

## Notifications & reminders
| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/reminders` 🔒 | Manage scheduled reminders |
| GET | `/notifications` 🔒 | In-app notification list |
| POST | `/notifications/read` 🔒 | Mark read |
| POST | `/devices/push-token` 🔒 | Register Expo push token |

## Subscriptions & payments
| Method | Path | Purpose |
|---|---|---|
| GET | `/subscription` 🔒 | Current plan/status |
| POST | `/subscription/checkout` 🔒 | Start Stripe/IAP checkout |
| POST | `/subscription/mpesa/stk-push` 🔒 | Initiate M-PESA STK Push |
| POST | `/webhooks/stripe` | Stripe events (no auth; verify signature) |
| POST | `/webhooks/mpesa` | Daraja callback (no auth; validate source) |

## Settings & data rights
| Method | Path | Purpose |
|---|---|---|
| GET/PATCH | `/settings` 🔒 | Preferences (dark mode, notif toggles…) |
| POST | `/data/export` 🔒 | Request full export (async → download) |
| DELETE | `/account` 🔒 | Delete account + all data |

## Admin  👑
| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/users` | Manage users |
| GET | `/admin/subscriptions` | Manage subscriptions |
| GET/POST | `/admin/moderation` | Review reports, take action |
| GET | `/admin/analytics` | Usage metrics |
| POST | `/admin/announcements` | Send announcements |

## Sync
| Method | Path | Purpose |
|---|---|---|
| GET | `/sync?since=<ts>` 🔒 | All changed rows across the user's data |
| POST | `/sync/push` 🔒 | Flush the client's offline write queue |
