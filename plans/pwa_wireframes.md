Below are detailed wireframes for each core page of the Next.js PWA. These layouts balance functionality, mobile-responsiveness, and our Microsoft PWA best practices.

---

## 1. Login Page

```
+--------------------------------------------------+
| Logo (centered)                                  |
|                                                  |
|  [ API Key Input Field         ]                 |
|                                                  |
|  [        Login Button         ]                 |
|                                                  |
|                    Version X.Y.Z                 |
+--------------------------------------------------+
```

- **Elements**:
  - App logo at top for branding
  - Single input for API key (type=password style)
  - Prominent primary button (accent1 `#129990`)
  - Footer with build/version info
- **Behavior**:
  - Disable Login button until input is non-empty
  - Validation error inline for invalid key
  - On success, redirect to `/`

---

## 2. Library Page (`/`)

```
+--------------------------------------------------+
| Navbar: [Library] [Upload] [Downloads] [Logout]  |
+--------------------------------------------------+
| Search Bar: [🔍  Search books...]                |
+--------------------------------------------------+
| Grid of BookCards (2–4 columns on desktop, 1 on mobile)
| +----------------+ +----------------+             |
| | Thumbnail      | | Thumbnail      |             |
| | Title          | | Title          |             |
| | Status Tag     | | Progress Bar   |             |
| | [▶ Play] [⬇]   | | [▶ Play] [⬇]   |             |
| +----------------+ +----------------+             |
+--------------------------------------------------+
```

- **Elements**:
  - **Navbar** with active state on Library
  - **Search**: real-time filter
  - **BookCard**: thumbnail, title, status badge (completed/processing), linear progress bar
  - **Actions**: Play (if completed), Download toggle, local Delete icon
- **Responsive**: fluid grid with Tailwind `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`

---

## 3. Upload Page (`/upload`)

```
+--------------------------------------------------+
| Navbar: [Library] [Upload (active)] [Downloads]   |
+--------------------------------------------------+
| Drag & Drop Zone                                |
| +----------------------------------------------+ |
| |  📂 Drop PDF/EPUB/TXT here or click to browse | |
| +----------------------------------------------+ |
|                                                  |
| Title: [__________________________]             |
| Format: ( • PDF   • EPUB   • TXT )              |
|                                                  |
| [ Start Upload ]                                 |
|                                                  |
| { Upload Progress Bar with % and speed }        |
+--------------------------------------------------+
```

- **Elements**:
  - **Dropzone** support drag/drop + file browser
  - **Form Fields**: Title input, format radio buttons
  - **Upload Button**: disabled until form valid
  - **Progress UI**: streaming progress + cancel option

---

## 4. Book Detail & Player Page (`/books/[id]`)

```
+--------------------------------------------------+
| Navbar: [Library] ...                            |
+--------------------------------------------------+
| ← Back      My Sample Book                      |
+--------------------------------------------------+
| Metadata:                                      |
| • Created: 2025‑06‑24   • Duration: 01:23:45    |
+--------------------------------------------------+
| [ Audio Player Component ]                      |
|  ┌────────────────────────────────────────────┐  |
|  │ ◀  Play/Pause  ▶  [───────────────]   00:12 │  |
|  │ [←15s]    [Speed:1×▼]   [Bookmark]   [→15s]│  |
|  └────────────────────────────────────────────┘  |
+--------------------------------------------------+
| Bookmarks:                                     |
| • Chapter 1 – 00:00        [Go] [Delete]       |
| • Interesting Fact – 02:34  [Go] [Delete]       |
+--------------------------------------------------+
| Download for offline: [ Toggle ]                |
+--------------------------------------------------+
```

- **Elements**:
  - **Back link** to Library
  - **Audio Player**:
    - Play/pause, skip ±15s, progress bar, time
    - Speed selector dropdown
    - Bookmark toggle button
  - **Bookmark List**: persisted points with quick navigation
  - **Offline Toggle**: write/remove chunks to IndexedDB

---

## 5. Downloads Manager (`/downloads`)

```
+--------------------------------------------------+
| Navbar: [Library] [Upload] [Downloads (active)]  |
+--------------------------------------------------+
| Total Offline Storage: 120 MB    [Clear All]     |
+--------------------------------------------------+
| List of Downloaded Books:                     |
| ┌────────────────────────────────────────────┐  |
| │ Thumbnail  Title       Size 01:23   [Delete]│  |
| └────────────────────────────────────────────┘  |
| ┌────────────────────────────────────────────┐  |
| │ Thumbnail  Another Book Size 45 MB [Delete]│  |
| └────────────────────────────────────────────┘  |
+--------------------------------------------------+
```

- **Elements**:
  - **Storage Indicator**: total bytes used, auto-warn at \~80% of iOS cache limit
  - **Clear All**: bulk remove
  - **List**: each entry shows title, size, duration, delete button

---

These wireframes map out all core pages and interactions for our Next.js PWA, ensuring clear navigation, offline-first capabilities, iOS-friendly behaviors, and scalability for future features.

\`
