# Repository Guidelines

## Project Structure & Module Organization

```
flux-ui/
├── backend/                # FastAPI Python service
│   ├── app/
│   │   ├── main.py              # App entry, lifespan, middleware, WebSocket endpoint
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── models.py            # ORM models (ImageRecord, TaskRecord, etc.)
│   │   ├── logger.py            # Rotating file and console logger
│   │   ├── websocket_manager.py # WS connection manager and broadcast
│   │   ├── routers/             # API route modules (generate, images, prompts, ...)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   └── services/            # Business logic (generator, task_queue, model_scanner)
│   ├── data/                    # SQLite database (mflux.db)
│   ├── output/                  # Generated images
│   ├── uploads/                 # Uploaded reference images
│   └── requirements.txt
├── frontend/               # Vue 3 + Vite SPA
│   ├── src/
│   │   ├── main.js              # App bootstrap
│   │   ├── App.vue               # Root layout with sidebar
│   │   ├── router/              # Vue Router config (7 routes)
│   │   ├── stores/              # Pinia stores (app state, theme)
│   │   ├── views/               # Page components (Text2Img, Img2Img, History, ...)
│   │   ├── components/          # Reusable UI (ImagePreview, ParameterPanel, TaskPanel)
│   │   ├── api/                 # Axios HTTP client
│   │   └── styles/              # Global CSS
│   └── vite.config.js           # Dev proxy to backend :8765
├── tests/                  # E2E test suite
│   ├── test_mflux.py            # Playwright + API tests
│   └── test_input.png           # Sample image for img2img tests
└── start.sh                # One-command launcher (backend + frontend)
```

The backend uses SQLite by default (`data/mflux.db`). Static files (generated images, uploads) are served via FastAPI `StaticFiles` mounts at `/api/output` and `/api/files`. The frontend proxies `/api` and `/ws` to the backend during development.

## Architecture Overview

MFlux Studio is a local-first Flux AI image generation UI. The Vue frontend sends prompts to a FastAPI backend, which queues generation tasks and streams progress over WebSocket. Completed images appear in a live preview and persist to the history gallery.

- **Task Queue:** In-process FIFO queue processes one generation at a time. WebSocket delivers real-time `progress`, `completed`, or `failed` events.
- **Model Scanning:** Scans a configurable directory for MLX-compatible Flux models and registers them in the database.
- **Prompt Enhancement:** A heuristic (not an LLM) rewrites short prompts into detailed English or Chinese variants.

## Build, Test, and Development Commands

- **Start everything:** `./start.sh` installs dependencies and launches both services.
- **Frontend only:** `npm run dev` in `frontend/` starts Vite on `:5173`.
- **Backend only:** `uvicorn app.main:app --reload` in `backend/` starts FastAPI on `:8765`.
- **Run E2E tests:** `python tests/test_mflux.py` from the repo root (requires both servers running and `npx playwright install firefox`).

The frontend dev server proxies `/api` and `/ws` to the backend, so two terminals (or `start.sh`) suffice for full-stack development.

## Coding Style and Naming Conventions

**Python (backend):** 4-space indent, type hints on all functions, snake_case for DB columns, `APIRouter` instances named `router` in each route module.

**JavaScript / Vue (frontend):** 2-space indent, single quotes, PascalCase for component filenames (`ImagePreview.vue`), lowercase route paths (`/text2img`), Pinia stores with composition API.

No linter config is committed yet. Recommended: `ruff` for Python, `prettier` and `eslint` for JS.

## Testing Guidelines

- **Framework:** Playwright (`sync_playwright`) for E2E tests.
- **Test file:** `tests/test_mflux.py` -- a standalone script covering API health, CRUD, generation flows, and UI assertions.
- **Naming:** `test_*` prefix with snake_case (`test_api_health`, `test_ui_navigation`).
- **Coverage:** API contracts, task lifecycle (queued to completed/failed), seed determinism, cancellation, and critical UI paths.

## Commit and Pull Request Guidelines

Use conventional commits: `type(scope): description`. For example, `feat(backend): add img2img strength parameter` or `fix(frontend): correct prompt textarea overflow`. Scope is `backend`, `frontend`, or `tests`. Keep PRs focused on one concern, link related issues, and include screenshots for UI changes.

## Security and Configuration Tips

- Environment variables live in `backend/.env` (not committed): `HOST`, `PORT`, `DATABASE_URL`, `OUTPUT_DIR`, `UPLOAD_DIR`.
- CORS allows all origins (`allow_origins=["*"]`) -- acceptable for local use, but tighten if exposed on a network.
- Uploaded images are unauthenticated; the tool is designed for single-user local use.
- The generator service requires the `mflux` CLI in `PATH`.
