# 🌾 KisanMind — AI Farmer Assistant

An AI-powered assistant for Indian farmers, with five agents:

- 🌱 **Soil Sense** — best crop, fertilizer & irrigation from soil readings (ML + LLM)
- 💬 **Kisan Chat** — Hindi/Hinglish chatbot for farming questions
- 🩺 **Crop Doctor** — diagnose disease from a photo
- 💰 **Mandi Bhav** — live mandi prices + selling advice
- 🏛️ **Sarkari Yojana** — info on government schemes for farmers

Built with **Flask + Groq + scikit-learn** and a single **Tailwind HTML** frontend served by the same app.

---

## 🚀 Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env and add your real keys
python app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## 🔑 Required environment variables

| Variable            | Required | Where to get it                                    |
| ------------------- | -------- | -------------------------------------------------- |
| `GROQ_API_KEY`      | Yes      | https://console.groq.com                           |
| `DATA_GOV_API_KEY`  | Yes      | https://data.gov.in (used for live mandi prices)   |
| `GEMINI_API_KEY`    | No       | https://aistudio.google.com/app/apikey (optional)  |

> ⚠️ Never commit your real keys. `.env` is git-ignored. Use `.env.example` as a template.

---

## ☁️ Deploy to Render

This repo includes a ready-to-use `render.yaml`.

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo.
3. Render reads `render.yaml` and creates a free web service.
4. In the Render dashboard, set the secret env vars (`GROQ_API_KEY`, `DATA_GOV_API_KEY`, optional `GEMINI_API_KEY`).
5. Deploy. Your app will be live at `https://<your-service>.onrender.com`.

Render uses `gunicorn app:app` to start the server and `/health` as the health-check path.

---

## 📦 Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

The `.gitignore` already excludes `.env`, the `uploads/` folder, the Windows `a.exe`, the empty `disease_model.h5` placeholder, and the `zipFile.zip` archive — so nothing sensitive or oversized gets pushed.

---

## 🗂️ Project structure

```
app.py                 # Flask backend (serves API + index.html)
index.html             # Single-page Tailwind frontend
soil_agent.py          # Soil + crop recommendation agent
chat.py                # Hindi/Hinglish chatbot
crop_doctor.py         # Disease diagnosis from image
mandi_bhav.py          # Live mandi prices + advice
sarkari_yojana.py      # Government schemes advisor
predict.py             # ML crop predictor (loads crop_model.pkl)
train.py               # Train the ML model from Crop_recommendation.csv
crop_model.pkl         # Pre-trained scikit-learn model
Crop_recommendation.csv
requirements.txt
Procfile               # Used by Render / Heroku-style hosts
render.yaml            # Render Blueprint config
runtime.txt            # Python version pin
.env.example           # Template for environment variables
.gitignore
```
