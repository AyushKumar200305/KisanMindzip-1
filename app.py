import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import your agents
from soil_agent import soil_sense_agent
from chat import chat_with_kisan, reset_chat
from crop_doctor import crop_doctor_agent
from mandi_bhav import mandi_bhav_agent
from sarkari_yojana import sarkari_yojana_agent

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
