# 🌾 KisanMind — AI-Powered Farming Assistant for Indian Farmers

<div align="center">

![KisanMind Banner](https://img.shields.io/badge/KisanMind-AI%20Farming%20Assistant-green?style=for-the-badge&logo=leaf)
![HackIndia](https://img.shields.io/badge/HackIndia-Spark%206%20NCR%20Central-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)
![Groq](https://img.shields.io/badge/Groq-LLaMA%204-purple?style=for-the-badge)

**🚀 Live Demo → [kisanmind-zbj7.onrender.com](https://kisanmind-zbj7.onrender.com)**

</div>

---

## 🧠 What is KisanMind?

KisanMind is an AI-powered farming assistant built for Indian farmers. It combines **Large Language Models**, **Machine Learning**, **real-time APIs**, and a **bilingual (Hindi/English) interface** to solve real problems farmers face daily — from crop recommendations to disease detection to government scheme guidance.

> Built at **HackIndia Spark 6 — NCR Central Region** hosted at **NIT Delhi**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌱 **Crop Recommendation** | Enter N/P/K values + climate → ML model recommends best crop |
| 🔬 **Disease Detection** | Upload a crop photo → AI identifies disease + treatment (organic & chemical) |
| 💬 **KisanBot Chat** | Hindi/Hinglish farming chatbot powered by LLaMA 3.1 |
| 📊 **Mandi Bhav** | Live mandi prices from data.gov.in + GPS-based nearest mandi finder |
| 🏛️ **Sarkari Yojana** | Government scheme advisor — PM-Kisan, Kisan Credit Card, PMFBY & more |
| 🌦️ **Weather Widget** | Real-time weather + 24hr rain forecast |
| 🗺️ **Region Soil Advice** | City/GPS based soil & crop advice — bilingual, no LLM needed |

---

## 🛠️ Tech Stack

**Backend**
- Python 3.11, Flask 3.0, Gunicorn
- Groq API (LLaMA 4 Scout Vision + LLaMA 3.1 8B Instant)
- scikit-learn (crop recommendation ML model)
- OpenWeatherMap API, data.gov.in API

**Frontend**
- Single-page HTML/JS (Vanilla JS + Tailwind CSS via CDN)
- Chart.js for mandi price visualization
- Fully bilingual — Hindi 🇮🇳 / English 🇬🇧 toggle

**Deployment**
- Render (Web Service, Free Tier)
- Gunicorn with 2 workers, 120s timeout

---

## 🏗️ Architecture

```
KisanMind/
├── app.py              ← Flask server + all API routes
├── chat.py             ← KisanBot chatbot agent (Groq)
├── crop_doctor.py      ← Disease detection agent (Groq Vision)
├── mandi_bhav.py       ← Mandi prices agent (data.gov.in)
├── mandi_nearest.py    ← GPS-based nearest mandi finder
├── sarkari_yojana.py   ← Government schemes advisor
├── soil_agent.py       ← Soil analysis agent
├── region_soil.py      ← Region-based crop suggestions
├── predict.py          ← ML crop recommendation
├── crop_model.pkl      ← Trained scikit-learn model
├── schemes.json        ← Verified government schemes database
├── soil_data.json      ← Region-wise soil data
├── index.html          ← Complete frontend (SPA)
└── requirements.txt
```

---

## 🔌 API Endpoints

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/soil` | Crop recommendation from N/P/K + climate |
| POST | `/api/region-soil` | Region-based crop suggestions |
| POST | `/api/chat` | KisanBot conversation |
| POST | `/api/disease` | Crop disease detection from image |
| POST | `/api/mandi` | Live mandi prices |
| POST | `/api/mandi/nearest` | GPS-based nearest mandi |
| POST | `/api/yojana` | Government scheme advisor |
| GET | `/api/weather` | Current weather + rain forecast |
| GET | `/health` | Health check |

---

## ⚙️ Environment Variables

| Key | Purpose | Get it from |
|---|---|---|
| `GROQ_API_KEY` | All AI agents (LLaMA models) | [console.groq.com](https://console.groq.com) |
| `OPENWEATHER_API_KEY` | Weather widget | [openweathermap.org](https://openweathermap.org/api) |
| `DATA_GOV_API_KEY` | Live mandi prices | [data.gov.in](https://data.gov.in) |

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/HackIndia-Spark-6-2025-Eclipse-Genesis/hackindia-spark-6-ncr-central-region-eclipse-genesis.git
cd hackindia-spark-6-ncr-central-region-eclipse-genesis

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Fill in your API keys in .env

# 4. Run
python main.py
# App runs at http://localhost:5000
```

---

## 👥 Team — Eclipse Genesis

| Name | GitHub |
|---|---|
| Ayush Kumar | [@AyushKumar200305](https://github.com/AyushKumar200305) |
| Divyansh Tyagi | [@divyanshtyagi502](https://github.com/divyanshtyagi502) |
| Aditya Mundhe | [@ADITYA-MUNDHE-03](https://github.com/ADITYA-MUNDHE-03) |
| Mayank Fuliya | — |

---

## 🏆 Built At

**HackIndia Spark 6 — NCR Central Region**
Hosted at **NIT Delhi**

---

<div align="center">
Made with ❤️ for Indian farmers 🌾
</div>
