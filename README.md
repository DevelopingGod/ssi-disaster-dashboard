---
title: Natural-Disaster.io
emoji: 🌍
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# Natural-Disaster.io

An agentic disaster intelligence dashboard. Ask anything about current or historical natural disasters in plain language — any language — and get a structured briefing with events plotted on an interactive world map.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat&logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agentic_pipeline-4A90D9?style=flat)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38BDF8?style=flat&logo=tailwindcss&logoColor=white)

---

## What it does

Type a question — *"What earthquakes happened in Japan this week?"* or *"Show me active flood alerts globally"* — and the system:

1. Routes your query through a multi-node LangGraph agent pipeline
2. Pulls live or historical data from GDACS, USGS, and ReliefWeb
3. Filters, ranks, and synthesises events into a structured briefing
4. Plots matching events on an interactive Leaflet world map

Queries are understood in any language. All timestamps are UTC.

---

## Features

- **Natural-language queries** — no structured input required; any language supported
- **Live + historical coverage** — current global alerts (GDACS RSS), M2.5+ earthquakes (USGS), historical event archives (GDACS EventList)
- **Humanitarian context** — narrative reports from ReliefWeb surfaced alongside raw event data
- **Dual LLM with automatic fallback** — Groq `llama-3.3-70b-versatile` primary; falls back to Google Gemini `gemini-2.0-flash` on rate-limit or quota exhaustion with no user-visible error
- **Precise map filtering** — pins match exactly the events described in the text briefing; map clears on each new query
- **Multi-type queries** — "earthquakes and cyclones in Asia" correctly filters both text and map to only those types
- **Resizable split layout** — drag the chat/map divider; position persists to `localStorage`
- **Map layer switcher** — Dark, Light, Satellite, Terrain
- **Auto-briefing on load** — global disaster overview fetched automatically on first session open
- **Safety guardrail** — refuses evacuation, shelter, and life-safety guidance; directs users to authoritative sources
- **Per-IP rate limiting** — 30 requests/minute enforced server-side

---

## Architecture

The platform is built around a multi-node LangGraph agent pipeline. An incoming query is routed through a FastAPI endpoint, classified by an LLM router, dispatched to the appropriate data-fetching tools (live feeds, historical archives, or both), geo/type filtered, and synthesised into a structured briefing before being returned as JSON to the Next.js frontend.

**LLM calls** at every node try Groq first. On any rate-limit or quota error, `_invoke_with_fallback()` transparently retries with Gemini. If both providers are exhausted, `_BothProvidersExhausted` is caught and a readable message is returned — never an HTTP 500.

**Caching** (in-process, thread-safe `_TTLCache`):

| Feed | TTL |
|------|-----|
| GDACS RSS | 10 min |
| GDACS EventList | 10 min |
| USGS GeoJSON | 10 min |
| ReliefWeb | 30 min |

---

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| [GDACS RSS](https://www.gdacs.org/) | Live global alerts | All currently active disaster types |
| [GDACS EventList API](https://www.gdacs.org/) | Significant events by date range | Historical and recent window queries |
| [USGS Earthquake Feeds](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | M2.5+ earthquakes — day / week / month | Live and near-historical seismic events |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Near real-time VIIRS fire detections (~3 hr latency) | Active wildfire hotspots, clustered by 1° grid, ranked by fire radiative power |
| [ReliefWeb API](https://reliefweb.int/help/api) | Humanitarian situation reports | Narrative context enrichment |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- A [Groq API key](https://console.groq.com/) — free tier available
- A [Google AI Studio key](https://aistudio.google.com/app/apikey) for Gemini — free tier available

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/DevelopingGod/ssi-disaster-dashboard.git
cd ssi-disaster-dashboard
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys — see the table below.

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend && npm install
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | API key for Groq (primary LLM provider) |
| `GEMINI_API_KEY` | Yes | — | API key for Google Gemini (fallback LLM provider) |
| `FIRMS_MAP_KEY` | Yes | — | NASA FIRMS MAP key for fire detection data |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of allowed CORS origins |
| `LOG_LEVEL` | No | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

Example `.env`:

```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
FIRMS_MAP_KEY=your_firms_map_key
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

---

## Running locally

Start the backend and frontend in separate terminals.

**Backend** (port 8000):

```bash
uvicorn app.main:app --reload
```

**Frontend** (port 3000):

```bash
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard fetches an initial global briefing automatically on first load.

---

## API reference

### `POST /chat`

Submit a natural-language query.

**Request body:**

```json
{
  "query": "What major earthquakes happened in Turkey in the last month?",
  "conversation_history": []
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `query` | `string` | Yes | Max 600 characters; control characters stripped |
| `conversation_history` | `array` | No | Prior turns; capped server-side to 20 turns × 800 chars/turn |

**Success response `200`:**

```json
{
  "response": "### Earthquake — Turkey\nA magnitude 5.4 earthquake...",
  "events": [{ "event_id": "usgs-...", "event_type": "earthquake", ... }],
  "route_target": "live_tools",
  "warnings": [],
  "guardrail_violations": [],
  "unavailable_data_reasons": [],
  "conversation_history": [...]
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `422` | Request body fails Pydantic validation |
| `429` | Per-IP rate limit exceeded (30 req/min) |
| `503` | Live monitoring feeds temporarily unreachable |

### `GET /health`

Returns `{"status": "ok", "service": "disaster-io-backend"}`. Use for uptime checks and backend warm-up pings.

---

## Project structure

```
├── app/
│   ├── main.py                  # FastAPI app, CORS, rate limiter, /chat endpoint
│   ├── graph/
│   │   ├── graph.py             # LangGraph compiled graph definition
│   │   ├── nodes.py             # All graph nodes, LLM fallback logic,
│   │   │                        #   continent mapping, geo/type filters
│   │   ├── tools.py             # fetch_live_disasters, search_historical_events,
│   │   │                        #   fetch_humanitarian_context, TTLCache
│   │   └── state.py             # AgentState Pydantic model
│   └── models/
│       └── disaster.py          # DisasterEvent Pydantic model
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Landing page
│   │   ├── dashboard/page.tsx   # Dashboard: auto-load, resizable chat/map layout
│   │   └── globals.css          # Coffee Dark design system CSS variables & animations
│   ├── components/
│   │   ├── ChatPanel.tsx        # Chat UI, markdown rendering, rotating loading messages
│   │   ├── MapPanel.tsx         # Leaflet map, layer switcher, marker popups with lat/lon
│   │   └── Navbar.tsx
│   └── lib/
│       ├── api.ts               # sendChatQuery(), warmBackend()
│       └── types.ts             # TypeScript type definitions
├── .env.example
└── requirements.txt
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI |
| Agent orchestration | LangGraph |
| Primary LLM | Groq `llama-3.3-70b-versatile` |
| Fallback LLM | Google Gemini `gemini-2.0-flash` |
| LLM client libraries | `langchain_groq`, `langchain_google_genai` |
| Data models | Pydantic v2 |
| Frontend framework | Next.js 15 (App Router) + React 18 |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Map | Leaflet via `react-leaflet` |
| Markdown rendering | `react-markdown` |
| Icons | `lucide-react` |

---

## Roadmap

Possible future enhancements:

| Area | Notes |
|------|-------|
| Flood extent layers | Overlay Copernicus EMS flood mapping tiles on the map for active flood events |
| Push notifications | Browser push alerts for new high-severity GDACS events |
| Event timeline view | Chronological sidebar showing event progression over the selected window |
| Offline PWA support | Service worker caching of the last briefing for low-connectivity use |

---

## Security notes

- Rate limiting uses `request.client.host` (actual TCP peer). `X-Forwarded-For` is intentionally ignored to prevent IP spoofing.
- User input is sanitised before reaching the agent: control characters stripped, length capped at 600 characters.
- Conversation history is truncated server-side (20 turns, 800 characters/turn) regardless of what the client sends.
- The agent refuses evacuation routes, shelter advice, and life-safety instructions; it redirects users to local emergency services.

---

## License

MIT
