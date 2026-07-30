# TeachHub — PRD

## Original Problem Statement
Bilingual (Russian + English) social platform where teachers publish, share, and run interactive HTML-based assignments (quizzes, drag & drop, games, visualizations) inside secure sandboxed iframes. Guests browse/run without an account; registered teachers publish/edit/like/favorite/report; admins moderate.

## User Choices
- Auth: JWT email + password
- Admin: lightweight dashboard UI
- Default language: browser auto-detect (RU/EN toggle)
- Design: agent-decided (Neo-Brutalist pastel, Outfit/Manrope fonts)
- Seed demo content: yes

## Architecture
- Frontend: React 19 + TailwindCSS + react-i18next + Phosphor icons; Bearer token in localStorage (`th_token`).
- Backend: FastAPI, all routes under `/api`. Bearer JWT auth (also cookie-capable). bcrypt hashing.
- DB: MongoDB — collections users, tasks, likes, favorites, reports.

## User Personas
- Subject teacher (publishes/curates interactive lessons)
- Guest learner (browses + runs, no account)
- Admin (moderation)

## Core Requirements (static)
- Guest feed (newest first, 10/page pagination), title search + subject/grade filters via URL params, view counter increments on open, sandboxed iframe runner.
- Teacher: register/login, publish (title/subject/grade/desc≤500/html≤1MB/tags) with live preview, edit/delete own, like/favorite/report, profile (My Assignments/Favorites/Settings).
- Admin: stats, users management, reports moderation.

## Implemented (2026-07-27)
- ✅ Phase 1-7 complete: i18n RU/EN toggle, Neo-Brutalist UI, header/layout
- ✅ Auth: register/login/logout, JWT Bearer, bcrypt, admin seeding, protected-route loading guard
- ✅ Publishing: form + validation + side-by-side live iframe preview, create/edit/delete
- ✅ Feed & View: paginated feed, single view page, sandboxed iframe player, view counter
- ✅ Search & filters via URL params
- ✅ Social: like/unlike (one/user), favorites, counts on cards, profile tabs, report flow
- ✅ Lightweight admin dashboard (stats, users, reports)
- ✅ 15 seeded interactive assignments; test accounts seeded
- ✅ Backend 27/27 tests pass; frontend 13/13 flows pass

## Credentials
- Admin: admin@teachhub.com / admin12345
- Teacher: teacher@teachhub.com / teacher12345

## Implemented — Feature Set 4 (2026-07-30)
- ✅ Solid opaque backgrounds for all toasts, dialogs, and the profile dropdown (light + dark)
- ✅ Dark-mode contrast overhaul: accent-protection CSS so pastel covers keep dark icons/text, dark surfaces use light text; light theme unchanged
- ✅ Privacy split into TWO independent toggles — hide followers list / hide following list (hidden from other users, owner still sees)
- ✅ Profile avatar upload (object storage) + bio; shown on public profile, header trigger, and follower/following lists
- ✅ /app/DATABASE.md — full database schema documentation
- ✅ Verified: frontend 4/4 fixes 100%; backend 52/54 (1 obsolete renamed-field test, 1 flaky timeout)

## Implemented — Feature Set 3 (2026-07-30)
- ✅ Register confirm-password + eye show/hide toggles on all password fields
- ✅ Dark mode (theme toggle in header, CSS-variable neo-brutalist theme, persisted)
- ✅ Draft posts (is_draft): hidden from public feed/search/other users & 404 for guests; visible to author in Studio (badge) and own view
- ✅ Privacy: "Hide followers & following" setting; public profile hides lists/counts for others
- ✅ Studio polish: branding shows "TeachHub"; removed redundant fullscreen-preview eye; folder-delete confirmation dialog
- ✅ Edit page now has a Delete button (with confirm); opaque dialogs & profile dropdown
- ✅ Verified: 49/49 backend, 9/9 fixes + 5 regressions

## Implemented — Feature Set 2 (2026-07-29)
- ✅ Register confirm-password field + eye show/hide toggle on all password inputs (PasswordInput)
- ✅ Three post types: `html` (interactive iframe), `worksheet` (downloadable images/docs via object storage), `blog` (text + images). Publishable, type-specific rendering (PostContent), and usable as a feed search filter.
- ✅ Object storage integration (Emergent) for uploads: POST /api/upload, public GET /api/files/{id}
- ✅ Studio workspace at /workspace — 3-zone layout (top bar with logo/fullscreen-eye/account, folders panel with auto folders by type+subject and user-created folders, tasks list with pencil->edit, preview zone with fullscreen toggle)
- ✅ Folders CRUD (/api/folders)
- ✅ Follow/subscribe system: follow toggle, followers/following lists in Profile + Public Profile (/u/:id), and a "Following" feed tab (/api/feed/following)
- ✅ Verified: 43/43 backend tests, 15/15 new frontend flows. Polished demo worksheet + blog seeded.

## Backlog / Next (P1/P2)
- P1: Rate limiting (~100 req/min/IP), production CORS lockdown to frontend origin
- P1: Make storage calls async (httpx/threadpool) — currently sync requests block event loop
- P1: Split server.py into routers/services for maintainability (~770 lines)
- P2: Comments, forking, version history, analytics dashboards
- P2: Full WCAG audit; httpOnly-cookie auth hardening
