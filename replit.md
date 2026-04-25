# KisanMind

AI-powered farmer assistant for Indian farmers. A Flask backend serves a single-page HTML/JS frontend with five AI agents and weather/soil utilities.

## Architecture

- **Backend:** Flask app (`app.py`) served via Gunicorn on port 5000
- **Frontend:** Single `index.html` (Tailwind via CDN, vanilla JS) served from project root by Flask
- **ML model:** `crop_model.pkl` (scikit-learn) loaded by `predict.py` for crop recommendation
- **AI provider:** Groq (Llama models) for all chat/vision/advice agents

## Agents (all under `/api/*`)

| Route | Module | Purpose |
| --- | --- | --- |
| `POST /api/soil` | `soil_agent.py` + `predict.py` | Recommend crop from N/P/K + climate + advice |
| `POST /api/region-soil` | `region_soil.py` + `soil_data.json` | Region-based crop suggestions from city or GPS — pure dataset lookup, bilingual (no LLM) |
| `POST /api/chat`, `/api/chat/reset` | `chat.py` | Hindi/Hinglish farming chatbot (Groq llama-3.1-8b-instant) |
| `POST /api/disease` | `crop_doctor.py` | Detect crop disease from image — returns structured card (Groq llama-4-scout vision) |
| `POST /api/mandi`, `/api/mandi/by-location` | `mandi_bhav.py` | Live mandi prices (data.gov.in) + selling advice |
| `POST /api/mandi/nearest` | `mandi_nearest.py` + `mandi_cities.py` | GPS-based 3–5 nearest mandi prices (data.gov.in + estimated fallback) with bilingual advice + chart payload |
| `POST /api/yojana` | `sarkari_yojana.py` | Government scheme advisor |
| `GET\|POST /api/weather` | `app.py` | OpenWeather current + 24h rain forecast |
| `GET\|POST /api/soil-info` | `app.py` | Lat/lon → temperature, humidity (OpenWeather) + pH (SoilGrids/ISRIC) |
| `GET /health` | `app.py` | Health check |

## Required secrets

- `GROQ_API_KEY` — used by every AI agent
- `DATA_GOV_API_KEY` — live mandi prices
- `OPENWEATHER_API_KEY` — weather widget + soil-info temperature/humidity
- `GEMINI_API_KEY` — optional, only used by the unused `gemini_cropdoctor.py`

## Running

The `Start application` workflow runs:
```
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload --timeout 120 app:app
```

## Deployment

Configured for **autoscale** with: `gunicorn --bind=0.0.0.0:5000 app:app`.

## Recent changes

- 2026-04-25: Imported from Replit Agent. Configured Gunicorn workflow on port 5000, fixed deployment to point at `app:app` (was `main:app` which had no Flask app), and requested the three required API keys.
- 2026-04-25: Added auto-read TTS toggle and full Hindi/English UI + agent translation (`data-i18n` system in `index.html`, per-language system prompts in every agent). Each `/api/*` route now accepts a `language` field.
- 2026-04-25: Reworked the Sarkari Yojana agent to be search-first / AI-fallback. New `schemes.json` holds verified bilingual data (name, eligibility, benefits, steps) for 10 major central schemes. `sarkari_yojana.py` now keyword-matches the query against the JSON and returns a clean structured response from local data — no LLM, no hallucination. Only when no scheme matches does it fall back to the existing Groq advisor (with a strict "do not invent" instruction). Response includes `source` (`database` or `ai_fallback`) and `matched_schemes`.
- 2026-04-25: Removed Crop Doctor (text-based) feature. Kept `/api/disease` (image-based detection with structured card output). Renamed tab to "Disease Detection" / "रोग पहचान".
- 2026-04-25: Upgraded Mandi Bhav panel — crop and state text inputs replaced with styled dropdowns (12 crops, 28 states). Result now renders structured price cards (min/modal/max per mandi) plus AI advice bubble. Location-detected state is auto-selected in the state dropdown.
- 2026-04-25: Upgraded Sarkari Yojana panel — query text input replaced with scheme dropdown (10 schemes from schemes.json) + state dropdown. Custom question box toggles open/closed. Results rendered as structured cards (Eligibility / Benefits / Steps) parsed from the verified database response. CSS bubble animation extended to yojanaResult.
- 2026-04-25: Added GPS-based nearest-mandi feature for the hackathon demo. New `mandi_cities.py` (curated dataset of ~180 Indian mandi cities with lat/lon) and `mandi_nearest.py` (haversine sort, data.gov.in live fetch with state filter, deterministic per-commodity fallback prices, dedup of live-record matches, bilingual advice). New `POST /api/mandi/nearest` route in `app.py` with 15-min in-memory cache and input validation. Frontend got a Chart.js price-comparison bar chart, a "Find Nearest Mandis (GPS)" button, distance-sorted mandi cards, "best mandi" recommendation (which prefers verified live prices over estimated ones), data-source badge, and auto TTS reading the Hindi/English advice.
