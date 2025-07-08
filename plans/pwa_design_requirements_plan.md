# PWA Design Requirements & Implementation Plan

This document captures the design requirements, architectural plan, and next steps for the Next.js Progressive Web App (PWA) frontend of our audiobook generation service. It reflects our commitment to clear stakeholder communication, offline-first reliability (especially on iOS), and scalability for future features.

---

## 1. Objectives & Scope

- **Primary Goal**: Deliver a Next.js PWA that allows users to upload documents, monitor processing status, and stream or download audiobooks for offline listening.
- **Key Constraints**:
  - Use API-key authentication in MVP; swap in email/password or OAuth in Phase 5.
  - Full offline support (metadata + audio chunks) with user-managed storage.
  - Pre‑fetch audio chunks for smooth playback; resume on interruptions.
  - iOS-specific adaptations (50 MB cache cap, user-gesture playback, SW lifecycle).
  - Theming per Microsoft best practices with colors: `#FFFBDE`, `#90D1CA`, `#129990`, `#096B68`.

---

## 2. Functional Requirements

1. **Authentication**
   - API-key login form (Phase 1).
   - Future swap to email/password or OAuth (Phase 5).
2. **Library Listing**
   - List all uploaded books with title, status, progress.
   - Real-time search and filter.
3. **File Upload**
   - Drag‑and‑drop or browse for PDF, EPUB, TXT.
   - Title input, format selector, progress indicator.
4. **Status Monitoring**
   - Poll `/books/{id}/status` every 2s until `completed` or `failed`.
   - Display textual status and percentage.
5. **Audio Player**
   - Stream Ogg/Opus chunks with prefetch (N+1…N+3).
   - Controls: play/pause, skip ±15 s, speed selector (0.5×–2×), bookmarks.
   - Resume on network loss or PWA background.
6. **Offline Downloads**
   - Toggle per-book offline download.
   - IndexedDB storage for metadata and chunk binaries.
   - Downloads Manager: list, delete individual, clear all, show storage used.
7. **Bookmarks**
   - Create, list, navigate to time offsets; persisted in IndexedDB.
8. **Theming & Accessibility**
   - Use provided color palette; ensure WCAG contrast.
   - Responsive design: grid layouts, mobile-first.
9. **Service Worker & Caching**
   - Pre-cache app shell; runtime cache for API JSON and audio chunks.
   - Implement cache-first strategy for audio with LRU eviction.

---

## 3. Architectural Plan

- **Framework & Libraries**:
  - Next.js (TypeScript)
  - React Query (data fetching)
  - Tailwind CSS (theming & layout)
  - Workbox via `next-pwa` (SW integration)
  - Dexie.js (IndexedDB abstraction)

- **Code Structure**:
  - `/pages`
    - `index.tsx` (Library)
    - `upload.tsx` (Upload)
    - `books/[id].tsx` (Detail & Player)
    - `downloads.tsx` (Offline Manager)
    - `login.tsx` (Auth)
  - `/components`
    - `Navbar`, `BookCard`, `AudioPlayer`, `DownloadToggle`, `StorageManager`, `BookmarkList`
  - `/lib`
    - `api.ts` (REST wrapper)
    - `auth.ts` (AuthContext)
    - `db.ts` (IndexedDB schema)
  - `next.config.js` (PWA plugin, SW rules)
  - `tailwind.config.js` (color palette)

- **State & Data Flow**:
  - React Query for all HTTP requests and caching.
  - IndexedDB mirror of `books` and `chunks` for offline UI.
  - SW intercepts chunk requests to serve from cache/IDB.

---

## 4. Phased Rollout

| Phase | Duration | Features |
|---|---|---|
| **1. MVP** | 1 week | Auth (API key), Library, Upload, Status, Player w/ prefetch & resume |
| **2. Offline & Caching** | 1 week | SW & Workbox, IndexedDB downloads, Downloads Manager |
| **3. Theming & Accessibility** | 3 days | Apply color palette, responsive grids, ARIA/WCAG compliance |
| **4. iOS Enhancements** | 3 days | Cache monitoring (50 MB), gesture-based playback, `visibilitychange` resume |
| **5. Auth Upgrade** | TBD | Email/password or OAuth integration |
| **6. Advanced Player** | TBD | Bookmarks UI, speed control, queue management |
| **7. Monitoring & CI** | TBD | Lighthouse CI, GitHub Actions, Docker deployment |

---

## 5. Clarifying Questions

1. **Design Assets**: Do you have logo/branding assets or should I propose placeholder designs?
2. **Error States**: How should we display server-side pipeline errors in the player or library?
3. **Storage Limits**: Should we warn users when they approach a custom download cap (e.g. 500 MB) beyond iOS device limits?
4. **Future Features**: Are there other critical features to plan for now (e.g. social sharing, analytics)?

---

_Reminder_: We prioritize clear stakeholder communication, maintainable architecture, and robust offline behavior—especially on iOS—while laying a solid foundation for future feature growth.

