"""
Region-based crop suggestion module.

Pure-lookup advisor (NO LLM calls). Resolves a city or lat/lon to an Indian
state, then returns a structured, bilingual recommendation built from
soil_data.json. Existing /api/soil endpoint is untouched.
"""
import json
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_DATA_PATH = os.path.join(os.path.dirname(__file__), "soil_data.json")
_OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")


def _load_data() -> dict:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_DATA = _load_data()


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _pick_lang(language: str) -> str:
    return "en" if (language or "").lower().startswith("en") else "hi"


def _resolve_city_to_state(city: str) -> Optional[str]:
    if not city:
        return None
    key = _norm(city)
    state_key = _DATA["city_to_state"].get(key)
    if state_key:
        return state_key
    # Maybe the user typed a state name directly
    return _DATA["state_aliases"].get(key)


def _reverse_geocode_state(lat, lon) -> Optional[str]:
    if not _OPENWEATHER_API_KEY:
        return None
    try:
        r = requests.get(
            "http://api.openweathermap.org/geo/1.0/reverse",
            params={"lat": lat, "lon": lon, "limit": 1,
                    "appid": _OPENWEATHER_API_KEY},
            timeout=10,
        ).json()
        if isinstance(r, list) and r:
            state = r[0].get("state") or ""
            name = r[0].get("name") or ""
            return state, name
    except requests.RequestException as e:
        logger.warning("Reverse geocode failed: %s", e)
    return None


def _translate_crop_list(slugs, lang):
    out = []
    for slug in slugs or []:
        info = _DATA["crops"].get(slug)
        out.append(info[lang] if info else slug.title())
    return out


def _build_response(state_key: str, city_display: str, language: str,
                    fuzzy: bool = False) -> dict:
    lang = _pick_lang(language)
    state = _DATA["states"][state_key]
    soil_slug = state["soil"]
    soil = _DATA["soil_types"][soil_slug][lang]
    advice = _DATA["soil_advice"][soil_slug][lang]

    state_name = state["name"][lang]
    if not city_display:
        city_display = state_name

    location_label = (f"{city_display} ({state_name})"
                      if city_display.strip().lower() != state_name.strip().lower()
                      else state_name)

    notice = ""
    if fuzzy:
        notice = ("Exact location not found. Showing general state-level advice."
                  if lang == "en"
                  else "सटीक स्थान नहीं मिला। राज्य स्तर की सामान्य सलाह दिखाई जा रही है।")

    return {
        "ok": True,
        "language": lang,
        "location": location_label,
        "city": city_display,
        "state": state_name,
        "state_key": state_key,
        "soil": soil,
        "kharif": _translate_crop_list(state.get("kharif"), lang),
        "rabi":   _translate_crop_list(state.get("rabi"), lang),
        "zaid":   _translate_crop_list(state.get("zaid"), lang),
        "advice": advice,
        "notice": notice,
        "source": "structured_dataset",
    }


def region_soil_advice(city: Optional[str] = None,
                       lat=None, lon=None,
                       language: str = "hi") -> dict:
    """Main entry point."""
    lang = _pick_lang(language)

    # 1) City path
    if city and str(city).strip():
        state_key = _resolve_city_to_state(city)
        if state_key and state_key in _DATA["states"]:
            return _build_response(state_key, city.strip(), language, fuzzy=False)
        # Unknown city -> still try GPS fallback if provided, else error
        if lat is None or lon is None:
            return {
                "ok": False,
                "error": ("City not found in our database. Try the closest big city, "
                          "your state name, or use 'My Location'."
                          if lang == "en" else
                          "यह शहर हमारी सूची में नहीं है। नज़दीकी बड़ा शहर, अपने राज्य का नाम लिखें या 'मेरी लोकेशन' का उपयोग करें।"),
            }

    # 2) GPS path
    if lat is not None and lon is not None:
        geo = _reverse_geocode_state(lat, lon)
        if geo:
            state_raw, city_name = geo
            state_key = _DATA["state_aliases"].get(_norm(state_raw))
            if state_key and state_key in _DATA["states"]:
                return _build_response(state_key, city_name or state_raw,
                                       language, fuzzy=False)
            return {
                "ok": False,
                "error": ("Could not match your state to our dataset."
                          if lang == "en" else
                          "आपके राज्य का मिलान हमारे डेटा से नहीं हो पाया।"),
            }
        return {
            "ok": False,
            "error": ("Location service unavailable. Please type your city instead."
                      if lang == "en" else
                      "लोकेशन सेवा उपलब्ध नहीं है। कृपया अपना शहर लिखें।"),
        }

    return {
        "ok": False,
        "error": ("Provide a city name or use 'My Location'."
                  if lang == "en" else
                  "कृपया शहर का नाम लिखें या 'मेरी लोकेशन' दबाएँ।"),
    }
