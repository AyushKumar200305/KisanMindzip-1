import os
import time
import math
import logging
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your agents
from soil_agent import soil_sense_agent
from chat import chat_with_kisan, reset_chat
from crop_doctor import crop_doctor_agent
from mandi_bhav import mandi_bhav_agent
from mandi_nearest import get_nearest_mandis
from sarkari_yojana import sarkari_yojana_agent
from region_soil import region_soil_advice

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# ─────────────────────────────────────────
# Treatment mapping for Disease Detection
# (extends output only — does NOT modify detection logic)
# ─────────────────────────────────────────
TREATMENT_MAP = [
    (["leaf spot", "blight", "rust", "mildew", "smut", "rot", "fungus", "fungal",
      "फफूंद", "फफूँद", "धब्बा", "झुलसा", "गलन", "रतुआ", "कंडुआ"],
     {
         "type_en": "Fungicide",
         "type_hi": "फफूंदनाशक",
         "organic_en": "Spray Neem oil (5 ml/litre water) or Trichoderma viride (5 g/litre) every 7 days.",
         "organic_hi": "नीम का तेल (5 मिली/लीटर पानी) या ट्राइकोडर्मा (5 ग्राम/लीटर) हर 7 दिन में छिड़कें।",
         "chemical_en": "Spray Mancozeb 75% WP (2 g/litre) or Carbendazim 50% WP (1 g/litre). Repeat after 10–12 days if needed.",
         "chemical_hi": "मैन्कोजेब 75% WP (2 ग्राम/लीटर) या कार्बेन्डाजिम 50% WP (1 ग्राम/लीटर) छिड़कें। 10–12 दिन बाद ज़रूरत हो तो दोबारा करें।",
         "shop_query_en": "fungicide shop",
         "shop_query_hi": "फफूंदनाशक की दुकान",
     }),
    (["yellow", "chlorosis", "nitrogen deficiency",
      "पीला", "पीली", "पीलापन", "नाइट्रोजन की कमी", "पोषण की कमी"],
     {
         "type_en": "Nitrogen Fertilizer (Urea)",
         "type_hi": "नाइट्रोजन उर्वरक (यूरिया)",
         "organic_en": "Apply well-rotted farmyard manure or vermicompost (1–2 kg per plant). Spray panchagavya 3% as foliar feed.",
         "organic_hi": "गोबर की पकी हुई खाद या वर्मी-कम्पोस्ट (1–2 किग्रा प्रति पौधा) डालें। पंचगव्य 3% पत्तियों पर छिड़कें।",
         "chemical_en": "Apply Urea 46% — 25–50 kg/acre as top dressing, or spray 2% urea solution (20 g/litre) on leaves.",
         "chemical_hi": "यूरिया 46% — 25–50 किग्रा/एकड़ टॉप-ड्रेसिंग में डालें, या 2% यूरिया घोल (20 ग्राम/लीटर) पत्तियों पर छिड़कें।",
         "shop_query_en": "urea fertilizer shop",
         "shop_query_hi": "यूरिया खाद की दुकान",
     }),
    (["pest", "insect", "aphid", "borer", "caterpillar", "whitefly", "thrips", "mite",
      "कीट", "कीड़ा", "सूँडी", "सुंडी", "इल्ली", "माहू", "सफेद मक्खी"],
     {
         "type_en": "Pesticide / Insecticide",
         "type_hi": "कीटनाशक",
         "organic_en": "Spray Neem oil (5 ml/litre) + soap (1 g/litre), or release Trichogramma cards. Use yellow sticky traps.",
         "organic_hi": "नीम का तेल (5 मिली/लीटर) + साबुन (1 ग्राम/लीटर) छिड़कें, या ट्राइकोग्रामा कार्ड लगाएँ। पीले स्टिकी ट्रैप का उपयोग करें।",
         "chemical_en": "Spray Imidacloprid 17.8% SL (0.3 ml/litre) or Chlorpyriphos 20% EC (2 ml/litre). Follow safety waiting period.",
         "chemical_hi": "इमिडाक्लोप्रिड 17.8% SL (0.3 मिली/लीटर) या क्लोरपाइरीफॉस 20% EC (2 मिली/लीटर) छिड़कें। सुरक्षा प्रतीक्षा-अवधि का पालन करें।",
         "shop_query_en": "pesticide shop",
         "shop_query_hi": "कीटनाशक की दुकान",
     }),
    (["bacteria", "bacterial", "wilt",
      "जीवाणु", "बैक्टीरिया", "उकठा", "मुरझान"],
     {
         "type_en": "Bactericide",
         "type_hi": "जीवाणुनाशक",
         "organic_en": "Drench soil with cow-urine + jaggery solution (1:10) or Pseudomonas fluorescens (10 g/litre).",
         "organic_hi": "गोमूत्र + गुड़ का घोल (1:10) या स्यूडोमोनास फ्लोरोसेंस (10 ग्राम/लीटर) मिट्टी में डालें।",
         "chemical_en": "Spray Streptocycline (0.1 g/litre) + Copper Oxychloride (3 g/litre). Repeat after 10 days.",
         "chemical_hi": "स्ट्रेप्टोसाइक्लिन (0.1 ग्राम/लीटर) + कॉपर ऑक्सीक्लोराइड (3 ग्राम/लीटर) छिड़कें। 10 दिन बाद दोहराएँ।",
         "shop_query_en": "agriculture medicine shop",
         "shop_query_hi": "कृषि दवाई की दुकान",
     }),
    (["virus", "viral", "mosaic",
      "वायरस", "मोज़ेक", "मोजेक"],
     {
         "type_en": "Virus management — vector control",
         "type_hi": "वायरस प्रबंधन — वाहक कीट नियंत्रण",
         "organic_en": "Remove and burn infected plants. Spray Neem oil (5 ml/litre) to control sucking pests that spread the virus.",
         "organic_hi": "संक्रमित पौधे उखाड़ कर जला दें। वायरस फैलाने वाले रसचूसक कीटों के लिए नीम तेल (5 मिली/लीटर) छिड़कें।",
         "chemical_en": "Control vectors with Imidacloprid 17.8% SL (0.3 ml/litre). No direct chemical cure for the virus itself.",
         "chemical_hi": "वाहक कीटों के लिए इमिडाक्लोप्रिड 17.8% SL (0.3 मिली/लीटर) छिड़कें। वायरस का कोई सीधा रासायनिक इलाज नहीं है।",
         "shop_query_en": "pesticide shop",
         "shop_query_hi": "कीटनाशक की दुकान",
     }),
]

DEFAULT_TREATMENT = {
    "type_en": "General fertilizer / treatment",
    "type_hi": "सामान्य खाद / उपचार",
    "organic_en": "Apply well-rotted compost or vermicompost. Spray Jeevamrit / Panchagavya as a tonic every 10 days.",
    "organic_hi": "अच्छी पकी कम्पोस्ट या वर्मी-कम्पोस्ट डालें। हर 10 दिन में जीवामृत / पंचगव्य टॉनिक छिड़कें।",
    "chemical_en": "Visit your local Krishi Vigyan Kendra (KVK) or agri-shop with the photo to get an exact recommendation.",
    "chemical_hi": "सही सलाह के लिए तस्वीर लेकर अपने नज़दीकी कृषि विज्ञान केंद्र (KVK) या कृषि की दुकान पर जाएँ।",
    "shop_query_en": "agriculture fertilizer shop",
    "shop_query_hi": "खाद की दुकान",
}

HEALTHY_KEYWORDS = ["no disease", "healthy", "appears healthy",
                    "कोई रोग नहीं", "स्वस्थ"]


def _classify_treatment(disease_name: str, cause: str):
    """Return treatment dict or None when crop looks healthy."""
    text = f"{disease_name} {cause}".lower()
    if any(k in text for k in HEALTHY_KEYWORDS):
        return None
    for keywords, treatment in TREATMENT_MAP:
        if any(k.lower() in text for k in keywords):
            return treatment
    return DEFAULT_TREATMENT

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────
# Simple in-memory cache (TTL-based)
# ─────────────────────────────────────────
_cache: dict = {}

def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.time() < entry["expires"]:
        return entry["value"]
    return None

def _cache_set(key: str, value, ttl_seconds: int):
    _cache[key] = {"value": value, "expires": time.time() + ttl_seconds}

# ─────────────────────────────────────────
# Input validation helpers
# ─────────────────────────────────────────
def _safe_float(val, name):
    """Parse float; raise ValueError with field name on failure."""
    try:
        result = float(val)
        if math.isnan(result) or math.isinf(result):
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise ValueError(f"Invalid value for '{name}': {val!r}")


def _request_lang() -> str:
    """Return 'en' or 'hi' based on the current request payload/query."""
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    raw = (data.get("language")
           or request.values.get("language")
           or request.headers.get("X-Language")
           or "hi")
    return "en" if str(raw).lower().startswith("en") else "hi"


def _friendly_error(exc: Exception, lang: str | None = None) -> str:
    """Bilingual, safe-to-show message for every upstream/system failure
    (Groq 401, OpenWeather 401, quota, network, parse errors, etc.).
    The user never sees raw exception strings."""
    if lang is None:
        lang = _request_lang()
    return ("Service temporarily unavailable. Please try again later."
            if lang == "en" else
            "सेवा अस्थायी रूप से उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।")

# ─────────────────────────────────────────
# 1. SOIL SENSE AGENT
# ─────────────────────────────────────────
@app.route("/api/soil", methods=["POST", "OPTIONS"])
def soil_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        required = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
        for field in required:
            if field not in data or data[field] is None or str(data[field]).strip() == "":
                return jsonify({"error": f"Field '{field}' is required"}), 400

        N           = _safe_float(data["N"], "N")
        P           = _safe_float(data["P"], "P")
        K           = _safe_float(data["K"], "K")
        temperature = _safe_float(data["temperature"], "temperature")
        humidity    = _safe_float(data["humidity"], "humidity")
        ph          = _safe_float(data["ph"], "ph")
        rainfall    = _safe_float(data["rainfall"], "rainfall")

        result = soil_sense_agent(
            N=N, P=P, K=K,
            temperature=temperature,
            humidity=humidity,
            ph=ph,
            rainfall=rainfall,
            language=data.get("language", "hi")
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Soil agent error")
        return jsonify({"error": _friendly_error(e)}), 500

# ─────────────────────────────────────────
# 2. KISAN CHATBOT
# ─────────────────────────────────────────
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        language = data.get("language", "hi")
        reply = chat_with_kisan(message, language=language)
        return jsonify({"reply": reply})
    except RuntimeError as e:
        return jsonify({"error": _friendly_error(e)}), 502
    except Exception as e:
        logger.exception("Chat error")
        return jsonify({"error": _friendly_error(e)}), 500

@app.route("/api/chat/reset", methods=["POST", "OPTIONS"])
def reset_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        reset_chat()
        return jsonify({"status": "Chat reset successfully"})
    except Exception as e:
        logger.exception("Chat reset error")
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# 3. DISEASE DETECTION (image-based scan)
# ─────────────────────────────────────────
@app.route("/api/disease", methods=["POST", "OPTIONS"])
def disease_route():
    """
    Enhanced crop-disease detection endpoint.
    Accepts: image (required, multipart), crop (optional), language (optional "hi"/"en")
    Returns structured fields: disease_name, cause, solution, prevention + raw diagnosis.
    """
    if request.method == "OPTIONS":
        return "", 200

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    if not image.filename:
        return jsonify({"error": "Empty image file"}), 400

    language  = request.form.get("language", "hi")
    crop_name = (request.form.get("crop") or "").strip() or None

    image_path = f"temp_disease_{image.filename}"
    image.save(image_path)

    try:
        result = crop_doctor_agent(
            image_path,
            crop_name=crop_name,
            language=language,
            structured=True,
        )
    except Exception as e:
        logger.exception("Disease detection error")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

    is_en = (language or "").lower().startswith("en")
    treatment = _classify_treatment(
        result.get("disease_name", ""),
        result.get("cause", ""),
    )

    extra = {}
    if treatment is not None:
        extra = {
            "treatment_type": treatment["type_en"]      if is_en else treatment["type_hi"],
            "organic":        treatment["organic_en"]   if is_en else treatment["organic_hi"],
            "chemical":       treatment["chemical_en"]  if is_en else treatment["chemical_hi"],
            "shop_query":     treatment["shop_query_en"] if is_en else treatment["shop_query_hi"],
        }

    return jsonify({
        "disease_name": result.get("disease_name", ""),
        "cause":        result.get("cause", ""),
        "solution":     result.get("solution", ""),
        "prevention":   result.get("prevention", ""),
        "diagnosis":    result.get("diagnosis", ""),
        "crop":         result.get("crop", ""),
        **extra,
    })

# ─────────────────────────────────────────
# 4. MANDI BHAV AGENT
# ─────────────────────────────────────────

# Per-commodity price thresholds in ₹/quintal (modal price)
_PRICE_THRESHOLDS = {
    "wheat":     (2000, 2400),
    "rice":      (2200, 2800),
    "paddy":     (2000, 2500),
    "tomato":    (1500, 2500),
    "onion":     (1500, 2500),
    "potato":    (1000, 1800),
    "cotton":    (5500, 7000),
    "maize":     (1700, 2200),
    "soyabean":  (3800, 4800),
    "soybean":   (3800, 4800),
    "mustard":   (4500, 5800),
    "groundnut": (5500, 7000),
    "bajra":     (1900, 2400),
    "jowar":     (2500, 3200),
}

_PRICE_INSIGHT_MSG = {
    "high":   ("📈 Good time to sell your crop — prices are strong.",
               "📈 बेचने का अच्छा समय — कीमतें अच्छी हैं।"),
    "low":    ("📉 Prices are low — consider waiting if possible.",
               "📉 कीमतें कम हैं — हो सके तो थोड़ा इंतज़ार करें।"),
    "medium": ("➡️ Prices are average — sell if you need cash, otherwise watch the trend.",
               "➡️ कीमतें सामान्य हैं — ज़रूरत हो तो बेचें, वरना भाव पर नज़र रखें।"),
}

# ───── Price-trend persistence (small JSON file) ─────
import json as _json
_TREND_FILE = ".mandi_trend.json"

def _trend_load():
    try:
        with open(_TREND_FILE, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

def _trend_save(snap):
    try:
        with open(_TREND_FILE, "w", encoding="utf-8") as f:
            _json.dump(snap, f)
    except Exception as e:
        logger.warning("Could not persist mandi trend: %s", e)

_TREND_MSG = {
    "up":   ("↑ Prices are rising vs your last check.",
             "↑ पिछली बार से कीमतें बढ़ी हैं।"),
    "down": ("↓ Prices have fallen vs your last check.",
             "↓ पिछली बार से कीमतें गिरी हैं।"),
    "flat": ("→ Prices are roughly the same as your last check.",
             "→ कीमतें पिछली बार जैसी ही हैं।"),
    "new":  ("• First time you're checking this crop+state — trend will appear next time.",
             "• पहली बार इस फसल+राज्य की जाँच — अगली बार ट्रेंड दिखेगा।"),
}


def _build_price_trend(commodity: str, state: str, current_avg: float):
    """Compare current avg to last-seen snapshot and return trend dict."""
    if not current_avg or current_avg <= 0:
        return None
    key = f"{(commodity or '').strip().lower()}|{(state or '').strip().lower()}"
    snap = _trend_load()
    prev = snap.get(key)

    direction, diff_pct = "new", 0.0
    if isinstance(prev, dict) and prev.get("avg"):
        try:
            prev_avg = float(prev["avg"])
            if prev_avg > 0:
                diff_pct = ((current_avg - prev_avg) / prev_avg) * 100.0
                if diff_pct >= 2.0:
                    direction = "up"
                elif diff_pct <= -2.0:
                    direction = "down"
                else:
                    direction = "flat"
        except Exception:
            pass

    en, hi = _TREND_MSG[direction]
    result = {
        "direction":     direction,
        "current_avg":   round(current_avg, 2),
        "previous_avg":  round(float(prev["avg"]), 2) if isinstance(prev, dict) and prev.get("avg") else None,
        "previous_date": (prev or {}).get("date") if isinstance(prev, dict) else None,
        "change_pct":    round(diff_pct, 1),
        "message_en":    en,
        "message_hi":    hi,
    }
    # Persist new snapshot for next call
    snap[key] = {"avg": round(current_avg, 2), "date": time.strftime("%Y-%m-%d %H:%M")}
    _trend_save(snap)
    return result


def _to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def _build_price_insight(commodity: str, records: list):
    """Compute a simple high/medium/low insight from live mandi records."""
    if not records:
        return None

    modals, best_market = [], None
    best_price = -1.0
    for r in records:
        v = _to_float(r.get("modal_price"))
        if v and v > 0:
            modals.append(v)
            if v > best_price:
                best_price = v
                best_market = r.get("market") or r.get("district") or ""
    if not modals:
        return None

    avg = sum(modals) / len(modals)
    worst = min(modals)
    key = (commodity or "").strip().lower()
    thr = _PRICE_THRESHOLDS.get(key)

    if thr:
        low_thr, high_thr = thr
        if avg >= high_thr:
            level = "high"
        elif avg <= low_thr:
            level = "low"
        else:
            level = "medium"
    else:
        if best_price >= avg * 1.10:
            level = "high"
        elif worst <= avg * 0.90:
            level = "low"
        else:
            level = "medium"

    en, hi = _PRICE_INSIGHT_MSG[level]
    return {
        "level":         level,
        "best_price":    best_price,
        "best_market":   best_market or "",
        "average_price": round(avg, 2),
        "message_en":    en,
        "message_hi":    hi,
    }


@app.route("/api/mandi", methods=["POST", "OPTIONS"])
def mandi_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True) or {}
        commodity = (data.get("commodity") or "").strip()
        state     = (data.get("state") or "").strip()
        language  = data.get("language", "hi")
        if not commodity:
            return jsonify({"error": "Commodity is required"}), 400
        if not state:
            return jsonify({"error": "State is required"}), 400

        cache_key = f"mandi:{commodity.lower()}:{state.lower()}:{language}"
        cached = _cache_get(cache_key)
        if cached is not None:
            result = dict(cached)  # don't mutate the cached object
        else:
            result = mandi_bhav_agent(commodity=commodity, state=state, language=language)
            result["price_insight"] = _build_price_insight(commodity, result.get("live_prices") or [])
            _cache_set(cache_key, result, ttl_seconds=1800)  # 30-min cache for prices+advice

        # Trend is computed/refreshed every call so each visit updates the snapshot.
        insight = result.get("price_insight") or {}
        avg = insight.get("average_price") or 0
        result["price_trend"] = _build_price_trend(commodity, state, float(avg))
        return jsonify(result)
    except Exception as e:
        logger.exception("Mandi agent error")
        return jsonify({"error": _friendly_error(e)}), 500

# ─────────────────────────────────────────
# 5. SARKARI YOJANA AGENT
# ─────────────────────────────────────────
@app.route("/api/yojana", methods=["POST", "OPTIONS"])
def yojana_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        if not query:
            lang = _request_lang()
            return jsonify({"error": (
                "Please describe what scheme you're looking for "
                "(e.g. 'subsidy for tractor')."
                if lang == "en" else
                "कृपया बताएँ आप किस योजना की जानकारी चाहते हैं "
                "(जैसे 'ट्रैक्टर के लिए सब्सिडी')।"
            )}), 400
        result = sarkari_yojana_agent(
            query=query,
            state=data.get("state") or None,
            language=data.get("language", "hi"),
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("Yojana agent error")
        return jsonify({"error": _friendly_error(e)}), 500

# ─────────────────────────────────────────
# 4c. MANDI — NEAREST MANDIS BY GPS (distance-sorted, with fallback prices)
#     Returns: nearest 3–5 mandis, best mandi, average price,
#     bilingual selling advice, and a chart-ready payload for Chart.js.
# ─────────────────────────────────────────
@app.route("/api/mandi/nearest", methods=["POST", "OPTIONS"])
def mandi_nearest_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True) or {}
        commodity = (data.get("commodity") or "").strip()
        lat = data.get("lat")
        lon = data.get("lon")
        state = (data.get("state") or "").strip() or None
        language = data.get("language", "hi")
        try:
            limit = int(data.get("limit") or 5)
        except (TypeError, ValueError):
            limit = 5

        if not commodity:
            return jsonify({"ok": False, "error": "commodity is required"}), 400
        if (lat is None or lon is None) and not state:
            return jsonify({"ok": False,
                            "error": "Provide GPS coordinates (lat, lon) or a state."}), 400

        lat_f = lon_f = None
        if lat is not None and lon is not None:
            try:
                lat_f = _safe_float(lat, "lat")
                lon_f = _safe_float(lon, "lon")
            except ValueError as ve:
                return jsonify({"ok": False, "error": str(ve)}), 400

        if lat_f is not None:
            cache_key = f"mandi_near:{commodity.lower()}:{round(lat_f,2)}:{round(lon_f,2)}:{limit}"
        else:
            cache_key = f"mandi_near:{commodity.lower()}:state={state.lower()}:{limit}"

        cached = _cache_get(cache_key)
        if cached is not None:
            result = dict(cached)
        else:
            result = get_nearest_mandis(
                commodity=commodity,
                lat=lat_f,
                lon=lon_f,
                language=language,
                limit=limit,
                state=state,
            )
            if result.get("ok"):
                _cache_set(cache_key, result, ttl_seconds=900)  # 15 min

        # Always re-tag the language so localStorage changes take effect.
        result["language"] = "en" if str(language).lower().startswith("en") else "hi"
        status = 200 if result.get("ok") else 400
        return jsonify(result), status
    except Exception as e:
        logger.exception("Mandi nearest error")
        return jsonify({"ok": False, "error": _friendly_error(e)}), 500


# ─────────────────────────────────────────
# 4b. MANDI BHAV BY LOCATION (reverse-geocode → state, then reuse mandi agent)
# ─────────────────────────────────────────
@app.route("/api/mandi/by-location", methods=["POST", "OPTIONS"])
def mandi_by_location_route():
    if request.method == "OPTIONS":
        return "", 200
    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OPENWEATHER_API_KEY not configured on the server."}), 500
    try:
        data = request.get_json(silent=True) or {}
        commodity = (data.get("commodity") or "").strip()
        lat = data.get("lat")
        lon = data.get("lon")

        if not commodity:
            return jsonify({"error": "commodity is required"}), 400
        if lat is None or lon is None:
            return jsonify({"error": "lat and lon are required"}), 400

        # Reverse-geocode lat/lon → state (uses existing OpenWeather key)
        geo = requests.get(
            "http://api.openweathermap.org/geo/1.0/reverse",
            params={"lat": lat, "lon": lon, "limit": 1,
                    "appid": OPENWEATHER_API_KEY},
            timeout=10
        ).json()
        if not isinstance(geo, list) or not geo:
            return jsonify({"error": "Could not resolve your location to a state."}), 400

        state = geo[0].get("state") or geo[0].get("name") or ""
        if not state:
            return jsonify({"error": "Could not detect state from location."}), 400

        # Reuse the existing mandi agent — no change to /api/mandi
        result = mandi_bhav_agent(
            commodity=commodity,
            state=state,
            language=data.get("language", "hi")
        )
        result["detected_state"] = state
        result["price_insight"] = _build_price_insight(commodity, result.get("live_prices") or [])
        avg = (result.get("price_insight") or {}).get("average_price") or 0
        result["price_trend"] = _build_price_trend(commodity, state, float(avg))
        return jsonify(result)
    except requests.RequestException:
        logger.exception("Mandi-by-location: upstream unreachable")
        return jsonify({"error": _friendly_error(Exception("network"))}), 503
    except Exception as e:
        logger.exception("Mandi-by-location: unexpected error")
        return jsonify({"error": _friendly_error(e)}), 500

# ─────────────────────────────────────────
# 6. WEATHER (OpenWeather)
# ─────────────────────────────────────────
@app.route("/api/weather", methods=["GET", "POST", "OPTIONS"])
def weather_route():
    if request.method == "OPTIONS":
        return "", 200

    lang = _request_lang()
    weather_unavailable = ("Weather data temporarily unavailable."
                           if lang == "en" else
                           "मौसम डेटा अभी उपलब्ध नहीं है।")
    invalid_loc = ("Invalid location. Please enter a valid city."
                   if lang == "en" else
                   "स्थान मान्य नहीं है। कृपया सही शहर दर्ज करें।")

    if not OPENWEATHER_API_KEY:
        return jsonify({"error": weather_unavailable}), 503

    # Accept lat/lon or city from either JSON body or query params
    data = request.get_json(silent=True) or {}
    lat = data.get("lat") or request.args.get("lat")
    lon = data.get("lon") or request.args.get("lon")
    city = data.get("city") or request.args.get("city")

    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}
    if lat and lon:
        params["lat"] = lat
        params["lon"] = lon
        cache_key = f"weather:ll:{round(float(lat),2)}:{round(float(lon),2)}"
    elif city:
        params["q"] = city
        cache_key = f"weather:city:{city.lower().strip()}"
    else:
        return jsonify({"error": invalid_loc}), 400

    cached = _cache_get(cache_key)
    if cached:
        return jsonify(cached)

    try:
        # Current conditions
        cur = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=params, timeout=10
        ).json()
        if str(cur.get("cod")) != "200":
            # Treat city-not-found and other lookup misses as invalid location;
            # everything else (401, 5xx, etc.) as a transient outage.
            cod = str(cur.get("cod"))
            if cod in ("404", "400"):
                return jsonify({"error": invalid_loc}), 400
            logger.warning("Weather upstream non-200: %s", cur)
            return jsonify({"error": weather_unavailable}), 503

        # Short-term forecast (next 24h, 3-hour steps) for rain prediction
        fc = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={**params, "cnt": 8}, timeout=10
        ).json()

        rain_chunks = []
        max_pop = 0.0
        if isinstance(fc.get("list"), list):
            for item in fc["list"]:
                pop = float(item.get("pop", 0))
                if pop > max_pop:
                    max_pop = pop
                rain_mm = (item.get("rain") or {}).get("3h", 0)
                if pop >= 0.3 or rain_mm > 0:
                    rain_chunks.append({
                        "time": item.get("dt_txt"),
                        "pop_percent": round(pop * 100),
                        "rain_mm_3h": rain_mm,
                        "desc": (item.get("weather") or [{}])[0].get("description", "")
                    })

        weather_main = (cur.get("weather") or [{}])[0]
        rain_now_mm = (cur.get("rain") or {}).get("1h", 0)

        will_rain = max_pop >= 0.4 or rain_now_mm > 0 or weather_main.get("main") in ("Rain", "Drizzle", "Thunderstorm")

        result = {
            "location": cur.get("name") or city or f"{lat},{lon}",
            "country": (cur.get("sys") or {}).get("country", ""),
            "temperature_c": cur.get("main", {}).get("temp"),
            "feels_like_c": cur.get("main", {}).get("feels_like"),
            "humidity_percent": cur.get("main", {}).get("humidity"),
            "wind_kph": round(cur.get("wind", {}).get("speed", 0) * 3.6, 1),
            "condition": weather_main.get("main", ""),
            "description": weather_main.get("description", ""),
            "icon": weather_main.get("icon", ""),
            "rain_now_mm_1h": rain_now_mm,
            "rain_prediction": {
                "will_rain_next_24h": will_rain,
                "max_probability_percent": round(max_pop * 100),
                "summary": (
                    f"Agle 24 ghante mein baarish ka chance: {round(max_pop * 100)}%"
                    if max_pop > 0 else
                    "Agle 24 ghante mein baarish ka koi major chance nahi hai."
                ),
                "rainy_slots": rain_chunks[:6]
            }
        }
        _cache_set(cache_key, result, ttl_seconds=600)  # 10-min weather cache
        return jsonify(result)
    except requests.RequestException:
        logger.exception("Weather service unreachable")
        return jsonify({"error": weather_unavailable}), 503
    except Exception:
        logger.exception("Weather route error")
        return jsonify({"error": weather_unavailable}), 500

# ─────────────────────────────────────────
# 7. SOIL INFO BY LOCATION (OpenWeather + SoilGrids)
# ─────────────────────────────────────────
@app.route("/api/soil-info", methods=["GET", "POST", "OPTIONS"])
def soil_info_route():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    lat = data.get("lat") or request.args.get("lat")
    lon = data.get("lon") or request.args.get("lon")
    if not (lat and lon):
        return jsonify({"error": "Provide lat and lon"}), 400

    result = {
        "source": {},
        "notes": "Temperature, humidity aur pH real data hain. N/P/K aur rainfall typical Indian averages hain — apne soil test ke hisaab se adjust karein."
    }

    # 1) Weather → temperature + humidity (real-time)
    try:
        if OPENWEATHER_API_KEY:
            w = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "units": "metric",
                        "appid": OPENWEATHER_API_KEY},
                timeout=10
            ).json()
            if str(w.get("cod")) == "200":
                result["temperature"] = w.get("main", {}).get("temp")
                result["humidity"] = w.get("main", {}).get("humidity")
                result["source"]["weather"] = "OpenWeather"
    except requests.RequestException:
        pass

    # 2) SoilGrids (ISRIC) → real pH at 0-5 cm
    try:
        sg = requests.get(
            "https://rest.isric.org/soilgrids/v2.0/properties/query",
            params=[("lon", lon), ("lat", lat),
                    ("property", "phh2o"), ("depth", "0-5cm"),
                    ("value", "mean")],
            timeout=15
        ).json()
        layers = (sg.get("properties") or {}).get("layers", [])
        for layer in layers:
            depths = layer.get("depths") or []
            if not depths:
                continue
            mean = (depths[0].get("values") or {}).get("mean")
            if mean is None:
                continue
            d_factor = (layer.get("unit_measure") or {}).get("d_factor", 1) or 1
            if layer.get("name") == "phh2o":
                # phh2o is reported as pH * 10
                result["ph"] = round(mean / d_factor, 2)
                result["source"]["ph"] = "SoilGrids (ISRIC)"
    except requests.RequestException:
        pass

    # 3) Sensible Indian-average estimates for fields with no free location API
    result.setdefault("N", 80)
    result.setdefault("P", 40)
    result.setdefault("K", 40)
    result.setdefault("rainfall", 200)

    return jsonify(result)

# ─────────────────────────────────────────
# 8. REGION-BASED SOIL ADVISOR (city or GPS → state-level structured advice)
#    Pure dataset lookup — no LLM, no random output.
# ─────────────────────────────────────────
@app.route("/api/region-soil", methods=["POST", "OPTIONS"])
def region_soil_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json(silent=True) or {}
        city = (data.get("city") or "").strip() or None
        lat = data.get("lat")
        lon = data.get("lon")
        language = data.get("language", "hi")

        result = region_soil_advice(city=city, lat=lat, lon=lon, language=language)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status
    except Exception as e:
        logger.exception("Region soil error")
        return jsonify({"ok": False, "error": _friendly_error(e)}), 500


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "KisanMind Backend Running",
        "agents": [
            "POST /api/soil",
            "POST /api/chat",
            "POST /api/chat/reset",
            "POST /api/disease",
            "POST /api/mandi",
            "POST /api/mandi/nearest",
            "POST /api/mandi/by-location",
            "POST /api/yojana"
        ]
    })

# ─────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
