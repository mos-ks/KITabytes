# A/MaTe

**Less files. More engineering insights.**

A/MaTe replaces static PDF test reports with living, interactive dashboards that update when new data arrives.

---

## The Problem

ZwickRoell performs 80 million materials tests per year. Each test generates a static PDF report that gets filed away. Engineers spend hours scrolling through documents, manually comparing results in Excel, and building reports from scratch every time.

## The Solution

A/MaTe is a conversational dashboard builder for materials testing data. Engineers describe what they want to analyze in natural language, confirm their dataset, and build interactive visualizations — all in under 2 minutes.

---

## How It Works

### 1. Select Your Data
Type what you need: *"Steel tensile tests from Company 3"*. The AI queries the database and shows a preview. Confirm it's the right dataset.

### 2. Build Your Dashboard
Click **Fill Canvas** for a standard overview, or build block-by-block. Each block offers preset visualizations (stress-strain curves, force summaries, modulus distributions) or a free-text custom request.

### 3. Live Updates
When new tests arrive, A/MaTe detects them automatically. Each affected chart shows a bell icon — click it to refresh that specific visualization with the new data. Update charts individually at your own pace.

### 4. Share, Don't Attach
Instead of emailing 50-page PDFs, share a dashboard link. Colleagues open the same interactive view with live data.

---

## Key Features

| Feature | What It Does |
|---|---|
| **AI Chat** | Natural language queries against your test database. Ask anything. |
| **Block-Based Dashboard** | Click "+" to add visualizations. Reorder, resize, remove freely. |
| **Fill Canvas** | One click generates a standard overview: stress-strain curves, max force, Young's modulus, strain at break. |
| **Custom Blocks** | Write any request: "Compare specimen width vs max force", "Generate a summary table", etc. |
| **Threshold Lines** | Set pass/fail limits on any chart. Red dashed line shows which specimens meet spec. |
| **Click-to-Explain** | Click any data point on a chart. The AI explains that specimen's properties and flags anything unusual. |
| **Auto-Insights** | After filling the dashboard, AI scans the data and surfaces anomalies, trends, and key statistics. |
| **Live Updates** | Detects new tests matching your filters. Per-chart bell icons let you refresh individual visualizations. |
| **Share Links** | Generate a URL that restores the full dashboard state for any colleague. |
| **Templates** | Save dashboard layouts. Load them on new data — instant reporting. |
| **PDF Export** | Print-ready export when you need a static document. |
| **Saved Dashboards** | Session history in the sidebar. Switch between analyses instantly. |

---

## Supported Visualizations

- **Stress-Strain Curves** — overlaid for all specimens with measurement data
- **Statistical Summaries** — bar charts with mean, std, min, max per specimen
- **Distributions** — histograms for any metric
- **Trend Analysis** — values over time with regression
- **Custom** — any free-text analysis request

---

## Architecture

```
Frontend (single HTML, CDN React + Plotly + Tailwind)
    ↕ REST API
Backend (Python FastAPI)
    ├── AI Agent (Gemini / OpenAI / Claude with tool-use)
    ├── Statistical Engine (scipy, numpy)
    └── MongoDB (pymongo / motor)
        └── ZwickRoell testXpert data
```

- **No build step** — single HTML file, zero npm/node runtime dependency
- **Any LLM** — supports Gemini, OpenAI, and Anthropic with automatic fallback
- **Real-time** — async MongoDB queries via Motor, WebSocket-ready architecture

---

## Why This Wins

| Criteria (Weight) | How A/MaTe Scores |
|---|---|
| **Creativity & Innovation (50%)** | Living dashboards replace static PDFs. Proactive anomaly detection. Click-to-explain intelligence. The "PDF killer" narrative. |
| **Viability & Feasibility (25%)** | Works today with real ZwickRoell data. Single-file frontend, standard Python backend. Production-ready patterns. |
| **Technical Sophistication (15%)** | LLM tool-use with 10 specialized functions. Real-time update detection. Unit-aware conversions (Pa→MPa→GPa). UUID-based channel resolution. |
| **Design (10%)** | Dark engineering-grade UI. Block-based dashboard builder. Bottom chat panel. Threshold lines. Professional data visualization. |

---

*Built at START Hack 2026 by KITabytes.*
