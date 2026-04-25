import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import your agents
from soil_agent import soil_sense_agent
from chat import chat_with_kisan, reset_chat
from crop_doctor import crop_doctor_agent
from mandi_bhav import mandi_bhav_agent
from sarkari_yojana import sarkari_yojana_agent

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────
# 1. SOIL SENSE AGENT
# ─────────────────────────────────────────
@app.route("/api/soil", methods=["POST", "OPTIONS"])
def soil_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json()
        result = soil_sense_agent(
            N=data["N"],
            P=data["P"],
            K=data["K"],
            temperature=data["temperature"],
            humidity=data["humidity"],
            ph=data["ph"],
            rainfall=data["rainfall"]
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# 2. KISAN CHATBOT
# ─────────────────────────────────────────
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json()
        message = data.get("message", "")
        reply = chat_with_kisan(message)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat/reset", methods=["POST", "OPTIONS"])
def reset_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        reset_chat()
        return jsonify({"status": "Chat reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# 3. CROP DOCTOR AGENT
# ─────────────────────────────────────────
@app.route("/api/crop-doctor", methods=["POST", "OPTIONS"])
def crop_doctor_route():
    if request.method == "OPTIONS":
        return "", 200

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    crop_name = request.form.get("crop_name", None)

    # Save image temporarily
    image_path = f"temp_{image.filename}"
    image.save(image_path)

    try:
        result = crop_doctor_agent(image_path, crop_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Always delete temp image
        if os.path.exists(image_path):
            os.remove(image_path)

    return jsonify(result)

# ─────────────────────────────────────────
# 4. MANDI BHAV AGENT
# ─────────────────────────────────────────
@app.route("/api/mandi", methods=["POST", "OPTIONS"])
def mandi_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json()
        result = mandi_bhav_agent(
            commodity=data["commodity"],
            state=data["state"]
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# 5. SARKARI YOJANA AGENT
# ─────────────────────────────────────────
@app.route("/api/yojana", methods=["POST", "OPTIONS"])
def yojana_route():
    if request.method == "OPTIONS":
        return "", 200
    try:
        data = request.get_json()
        result = sarkari_yojana_agent(
            query=data["query"],
            state=data.get("state", None)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────
# 6. WEATHER (OpenWeather)
# ─────────────────────────────────────────
@app.route("/api/weather", methods=["GET", "POST", "OPTIONS"])
def weather_route():
    if request.method == "OPTIONS":
        return "", 200

    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OPENWEATHER_API_KEY is not configured on the server."}), 500

    # Accept lat/lon or city from either JSON body or query params
    data = request.get_json(silent=True) or {}
    lat = data.get("lat") or request.args.get("lat")
    lon = data.get("lon") or request.args.get("lon")
    city = data.get("city") or request.args.get("city")

    params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}
    if lat and lon:
        params["lat"] = lat
        params["lon"] = lon
    elif city:
        params["q"] = city
    else:
        return jsonify({"error": "Provide either {lat, lon} or {city}."}), 400

    try:
        # Current conditions
        cur = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=params, timeout=10
        ).json()
        if str(cur.get("cod")) != "200":
            return jsonify({"error": cur.get("message", "Weather lookup failed")}), 400

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

        return jsonify({
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
        })
    except requests.RequestException as e:
        return jsonify({"error": f"Weather service unreachable: {e}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            "POST /api/crop-doctor",
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
