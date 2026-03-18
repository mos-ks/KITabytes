# A/MaTe — AI in Material Testing

**Less files. More engineering insights.**

A/MaTe replaces static PDF test reports with living, interactive dashboards. Engineers select data in natural language, build visualizations block-by-block, and get AI-powered insights — all in under 2 minutes.

Built at **START Hack 2026** by team **KITabytes** for the ZwickRoell challenge.

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for MongoDB)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- One AI API key: Anthropic, OpenAI, or Google Gemini

### 1. Database

```bash
docker compose up -d
```

This pulls and starts the pre-loaded MongoDB with ZwickRoell testXpert data (31K+ tests).

### 2. Backend

```bash
cp .env.example .env
# Edit .env — add your API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY)

uv sync
uv run uvicorn app.main:app --reload --app-dir backend
```

Backend runs at `http://localhost:8000`.

### 3. Frontend

```bash
cd frontend && npm install && npm run dev
```

Frontend runs at `http://localhost:5173`. The Vite dev server proxies `/api` to the backend.

---

## How It Works

### 1. Select Your Data
Type what you need: *"Steel tensile tests from Company 3"*. The AI queries the database, shows a preview table, and asks you to confirm.

### 2. Build Your Dashboard
Click **Fill Canvas** for a standard overview (stress-strain curves, max force, Young's modulus, strain at break), or add blocks one by one. Each block supports preset visualizations or free-text custom requests.

### 3. Interact
- **Click any data point** on a chart — the AI explains that specimen
- **Set threshold lines** to check pass/fail against specs
- **SPC control charts** with mean ± 3σ or custom UCL/LCL
- **Ask questions** in the chat sidebar about your data

### 4. Live Updates
When new tests arrive, each chart shows a bell icon. Click it to refresh that specific visualization with the new data.

### 5. Share
Generate a dashboard link or export to PDF. Colleagues open the same interactive view.

---

## Architecture

```
Frontend (single HTML, CDN React + Plotly + Tailwind)
    ↕ REST API
Backend (Python FastAPI + async MongoDB via Motor)
    ├── AI Agent (Claude / Gemini / OpenAI with tool-use)
    ├── Statistical Engine (scipy, numpy)
    └── MongoDB
        └── ZwickRoell testXpert data (31K tests, 215K value docs)
```

- **No build step** — single HTML file frontend, zero npm runtime dependency
- **Any LLM** — supports Claude, Gemini, and OpenAI with automatic fallback
- **10 AI tools** — query tests, compute statistics, detect outliers, analyze trends, compare groups

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, route mounting
│   │   ├── config.py            # Environment config (API keys, MongoDB)
│   │   ├── db.py                # Async MongoDB client (Motor)
│   │   ├── uuid_maps.py         # Channel UUID resolution
│   │   ├── routes/
│   │   │   ├── chat.py          # Chat + chart-data endpoints
│   │   │   └── data.py          # Direct data query endpoints
│   │   └── services/
│   │       ├── ai_service.py    # LLM orchestration + tool execution
│   │       ├── data_service.py  # MongoDB queries + metric resolution
│   │       └── stats_service.py # Descriptive stats, t-tests, outliers
│   └── tests/
├── frontend/
│   ├── index.html               # Single-file React app
│   ├── vite.config.ts           # Dev server + API proxy
│   └── package.json
├── mongodb/                     # Docker + SSL config for local DB
├── docs/                        # Backend walkthrough + DB schema
├── docker-compose.yml           # MongoDB container
├── pyproject.toml               # Python dependencies (uv)
└── .env.example                 # Environment template
```

---

## Testing

```bash
uv run pytest backend/tests -q
```

---

## Key Features

| Feature | Description |
|---|---|
| **Natural Language Queries** | Ask anything about your test data in plain English |
| **Block-Based Dashboard** | Add, reorder, resize, remove visualizations freely |
| **Fill Canvas** | One-click standard overview with 6 key charts |
| **SPC Control Charts** | Mean ± 3σ or custom UCL/LCL with out-of-control detection |
| **Per-Chart Live Updates** | Bell icon on each plot when new data arrives |
| **Click-to-Explain** | Click any data point for AI analysis |
| **Threshold Lines** | Set pass/fail limits on any chart |
| **Auto-Insights** | AI scans data and surfaces anomalies after dashboard fill |
| **Share Links** | URL-encoded dashboard state for colleagues |
| **Templates** | Save and load dashboard layouts |
| **PDF Export** | Print-ready static export |

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `MONGO_URI` | MongoDB connection string (default: `mongodb://localhost:27017`) |
| `MONGO_DB` | Database name (default: `txp_clean`) |

Only one AI provider key is required. The backend tries Gemini → Claude → OpenAI in order.

---

## Team

**KITabytes** — START Hack 2026
