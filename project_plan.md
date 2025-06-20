Below is a two-level project plan. First we establish the *overall boilerplate* and repo setup; then we break out a focused plan for each service in our Compose architecture. Each item includes suggested deliverables and rough sequencing so you can tackle them in an agile, incremental way.

---

## A. Boilerplate & Common Infrastructure (Sprint 0)

#### 1. Repository Layout & GitHub Setup

* **Tasks**

  * Create top-level repo with folders:

    ```
    audiobook-server/
    ├── services/
    ├── pwa-client/
    ├── docker-compose.yml
    ├── .env.example
    ├── README.md
    └── .github/
        └── workflows/
    ```
  * Add `.gitignore` (Python, node, Docker artifacts).
  * Commit initial README.md with project overview and high-level architecture diagram.

* **Deliverables**

  * Empty folder structure pushed to `main` branch.
  * Example `.env.example` listing `API_KEY` and other common env variables.
  * GitHub Actions workflow stub (`lint-and-test.yaml`).

#### 2. Shared Tools & CI

* **Tasks**

  * Configure GitHub Actions:

    * Python lint & test job (runs `flake8` or `black --check`, `pytest --maxfail=1`)
    * Node lint & build job for PWA (runs `npm run lint`, `npm run build`)
  * Add project-wide pre-commit hooks (e.g., `black`, `isort`, `prettier`).

* **Deliverables**

  * Passing CI on an empty scaffold.
  * Documentation in `CONTRIBUTING.md` with dev setup instructions.

#### 3. Docker Compose & Networking

* **Tasks**

  * Paste the cleaned-up Compose file into `docker-compose.yml`.
  * Define named volumes for `text_data`, `wav_data`, `segment_data`, `meta_data`.
  * Verify `docker compose up` creates all volumes and starts (empty) containers.

* **Deliverables**

  * All services appear “up” (even if they immediately crash) and share the network/volumes.
  * README section “Running with Docker Compose” validated.

---

## B. Per-Service Roadmap

For each service, follow this pattern: **Scaffold → Core Logic → Testing → Dockerfile → Integration**.

| Service | 1. Scaffold                                      | 2. Core Logic | 3. Tests | 4. Dockerfile | 5. Integrate |
| ------- | ------------------------------------------------ | ------------- | -------- | ------------- | ------------ |
| **API** | - `services/api/app.py` with FastAPI app factory |               |          |               |              |

* Auth middleware stub | - `POST /books`
* Status & chunk endpoints
* Read/write to `meta_data` and serve `/data/ogg` | - Pytest for each endpoint
* Mock volumes with tmpdirs | - Base Python 3.10 image
* `pip install -r requirements.txt`
* Entrypoint `uvicorn app:app` | - Update Compose to pass `API_KEY`
* Smoke test via cURL |
  \| **Ingest**   | - `services/ingest/main.py` CLI skeleton | - PDF→text via `pdfplumber`
* EPUB→text via `ebooklib`
* TXT read + `chardet`
* OCR fallback | - Unit tests feeding sample PDF/EPUB/TXT
* Validate correct Unicode output | - Python image with `poppler-utils` (for pdfplumber)
* Tesseract CLI install | - Hook into API’s processing queue (e.g. filesystem flag) |
  \| **Segmenter**| - `services/segmenter/main.py` CLI stub | - Sentence split with spaCy
* Chunk assembler (800 chars)
* SSML wrapper (`<s>`, `<break>`) | - Tests on paragraphs of varied length
* Verify chunk count & SSML tags | - Python image with spaCy model downloaded at build | - Watch `text_data`, output SSML metadata to `meta_data` |
  \| **TTS Worker**| - `services/tts-worker/worker.py` scaffold | - Load FastPitch+HiFiGAN once
* Consume SSML chunks, emit WAV to `wav_data` | - Smoke test WAV generation on dummy SSML | - NVIDIA base image
* Install model dependencies
* Expose any healthcheck port | - Trigger on new SSML entries in `meta_data` |
  \| **Transcoder**| - `services/transcoder/transcode.py` stub | - `transcode_and_segment()` wrapper around FFmpeg | - Use small WAV fixture, verify .ogg files count & duration | - Python image + `ffmpeg` package | - Consume WAV, output to `segment_data` & update `meta_data` |
  \| **Storage**  | - `services/storage/db.py` with SQLite schema | - Tables: `books`, `chunks` (seq, duration, path)
* Read/write helpers | - Unit tests for DB CRUD operations | - Python image with SQLite client installed | - Shared volume mounted in API, Ingest, etc. |

---

### C. Sprint Planning & Dependencies

1. **Sprint 1 (Days 1–3):**

   * Complete **Boilerplate**, CI, Compose setup.
   * Scaffold **API** service and Dockerfile.
   * Verify Compose starts API container without errors.

2. **Sprint 2 (Days 4–7):**

   * Finish **API** core endpoints + tests.
   * Scaffold **Ingest**, implement PDF/TXT extraction + tests.
   * Integrate Ingest with API (POST book → writes text).

3. **Sprint 3 (Days 8–11):**

   * Scaffold **Segmenter**, implement tokenizer, chunker + tests.
   * Wire Segmenter to Ingest outputs.
   * Scaffold **Storage** DB and hook API status endpoint into DB.

4. **Sprint 4 (Days 12–15):**

   * Scaffold **TTS Worker**, test WAV generation.
   * Scaffold **Transcoder**, test segment creation.
   * Integrate TTS→WAV→Transcoder pipeline and update metadata.

5. **Sprint 5 (Days 16–18):**

   * Finish **Client PWA** scaffold (Vite + React).
   * Implement book upload flow and status polling.
   * Wire PWA playback of `/chunks/{seq}`.

6. **Sprint 6 (Days 19–21):**

   * End-to-end smoke tests: upload PDF → stream audio.
   * Polish logging, error handling, and README.
   * Prepare demo instructions and handoff guide.

---

With this plan you can assign small, testable tasks to yourself or your team, make steady progress in two- to three-day sprints, and ensure each service cleanly integrates into the Compose network. Let me know if you’d like to adjust timelines or break any tasks into finer subtasks!
