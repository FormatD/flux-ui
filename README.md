# MFlux Studio

A local-first AI image generation UI for Flux models, powered by MLX.

Generate images from text prompts right on your Mac, with a real‑time progress feed, image history, prompt management, and full control over generation parameters.

## Features

- **Text‑to‑Image & Image‑to‑Image** – Generate from text prompts or remix uploaded images.
- **Batch Generation** – Produce multiple images per prompt with automatic seed variation.
- **Real‑Time Progress** – WebSocket stream delivers step‑by‑step progress and task notifications.
- **Image History & Browser** – Every generated image is saved and searchable.
- **Prompt Manager** – Save, categorise, and reuse prompts. Built‑in prompt enhancement heuristics.
- **Model Management** – Scan and select from locally cached MLX‑compatible Flux models.
- **Dark Mode** – Toggle between light and dark themes.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite, Element Plus, Pinia, Vue Router |
| Backend | Python, FastAPI, SQLAlchemy, WebSocket |
| Generation | Flux via `mflux` CLI (MLX‑accelerated) |
| Database | SQLite |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- `mflux` CLI installed (`pip install mflux`)
- A Flux model cached locally (the app will pull one on first generation)

### Launch

```bash
# One‑command start (installs dependencies and runs both services)
./start.sh

# Or start separately:
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # → http://localhost:8765

cd frontend
npm install
npm run dev                     # → http://localhost:5173
```

Open `http://localhost:5173` in your browser. The API docs are available at `http://localhost:8765/docs`.

## Project Structure

```
flux-ui/
├── backend/               # FastAPI service
│   ├── app/
│   │   ├── main.py            # App entry, middleware, WebSocket endpoint
│   │   ├── database.py        # SQLAlchemy engine & session
│   │   ├── models.py          # ORM models
│   │   ├── routers/           # API route modules
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Generator, task queue, model scanner
│   ├── output/                # Generated images
│   └── requirements.txt
├── frontend/              # Vue 3 SPA
│   ├── src/
│   │   ├── views/             # Page components
│   │   ├── components/        # Reusable UI
│   │   ├── stores/            # Pinia state
│   │   └── api/               # Axios client
│   └── vite.config.js
├── tests/                 # E2E test suite (Playwright)
├── AGENTS.md              # Contributor guide
└── start.sh               # Development launcher
```

## Testing

```bash
python tests/test_mflux.py
```

Requires both servers running and Playwright installed (`npx playwright install firefox`). The suite covers API health checks, CRUD operations, generation flows, and UI navigation.

## License

MIT
