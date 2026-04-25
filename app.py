import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from region_soil import region_soil_advice

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _request_lang() -> str:
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    raw = (data.get("language")
           or request.values.get("language")
           or request.headers.get("X-Language")
           or "hi")
    return "en" if str(raw).lower().startswith("en") else "hi"


def _friendly_error(lang: str | None = None) -> str:
    if lang is None:
        lang = _request_lang()
    return ("Service temporarily unavailable. Please try again later."
            if lang == "en" else
            "सेवा अस्थायी रूप से उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।")


# ─────────────────────────────────────────
# REGION-BASED CROP SUGGESTIONS (only feature)
# Pure dataset lookup — no LLM, no random output.
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
    except Exception:
        logger.exception("Region soil error")
        return jsonify({"ok": False, "error": _friendly_error()}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "KisanMind Backend Running",
        "agents": ["POST /api/region-soil"],
    })


@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
