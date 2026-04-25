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
| `POST /api/chat`, `/api/chat/reset` | `chat.py` | Hindi/Hinglish farming chatbot (Groq llama-3.1-8b-instant) |
| `POST /api/crop-doctor` | `crop_doctor.py` | Diagnose crop disease from image (Groq llama-4-scout vision) |
| `POST /api/mandi`, `/api/mandi/by-location` | `mandi_bhav.py` | Live mandi prices (data.gov.in) + selling advice |
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
