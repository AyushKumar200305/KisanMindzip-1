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
from sarkari_yojana import sarkari_yojana_agent
from region_soil import region_soil_advice

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

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

    return jsonify({
        "disease_name": result.get("disease_name", ""),
        "cause":        result.get("cause", ""),
        "solution":     result.get("solution", ""),
        "prevention":   result.get("prevention", ""),
        "diagnosis":    result.get("diagnosis", ""),
        "crop":         result.get("crop", ""),
    })

# ─────────────────────────────────────────
# 4. MANDI BHAV AGENT
# ─────────────────────────────────────────
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
        if cached:
            return jsonify(cached)

        result = mandi_bhav_agent(commodity=commodity, state=state, language=language)
        _cache_set(cache_key, result, ttl_seconds=1800)  # 30-min cache
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
