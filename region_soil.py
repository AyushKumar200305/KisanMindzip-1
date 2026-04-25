"""
Region-based crop suggestion module.

Pure-lookup advisor (NO LLM calls). Resolves a city or lat/lon to an Indian
state, then returns a structured, bilingual recommendation built from
soil_data.json. Existing /api/soil endpoint is untouched.
"""
import difflib
import json
import logging
import os
from typing import Optional, Tuple

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


def _fuzzy_city_match(key: str) -> Optional[str]:
    """Try to recover from common typos by finding the closest known city."""
    if not key:
        return None
    candidates = list(_DATA["city_to_state"].keys())
    matches = difflib.get_close_matches(key, candidates, n=1, cutoff=0.85)
    if matches:
        return _DATA["city_to_state"].get(matches[0])
    return None


def _geocode_city_to_state(city: str) -> Optional[Tuple[str, str]]:
    """Use OpenWeather forward geocoding to resolve a city (anywhere in India)
    to its state. Returns (state_key, resolved_city_name) or None."""
    if not _OPENWEATHER_API_KEY or not city:
        return None
    try:
        r = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": f"{city},IN", "limit": 5,
                    "appid": _OPENWEATHER_API_KEY},
            timeout=10,
        ).json()
        if not isinstance(r, list):
            return None
        for hit in r:
            if (hit.get("country") or "").upper() != "IN":
                continue
            state_raw = hit.get("state") or ""
            name = hit.get("name") or city
            state_key = _DATA["state_aliases"].get(_norm(state_raw))
            if state_key and state_key in _DATA["states"]:
                return state_key, name
    except requests.RequestException as e:
        logger.warning("Forward geocode failed: %s", e)
    return None


def _nominatim_city_to_state(city: str) -> Optional[Tuple[str, str]]:
    """Fallback geocoder using OpenStreetMap Nominatim. Covers Indian
    districts, towns and villages that OpenWeather may not have.
    Returns (state_key, resolved_city_name) or None."""
    if not city:
        return None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{city}, India", "format": "json",
                    "addressdetails": 1, "limit": 3, "countrycodes": "in"},
            headers={"User-Agent": "KisanMind/1.0 (region-soil-advisor)"},
            timeout=10,
        ).json()
        if not isinstance(r, list):
            return None
        for hit in r:
            addr = hit.get("address") or {}
            state_raw = addr.get("state") or ""
            name = (addr.get("city") or addr.get("town") or addr.get("village")
                    or addr.get("county") or addr.get("state_district")
                    or city)
            state_key = _DATA["state_aliases"].get(_norm(state_raw))
            if state_key and state_key in _DATA["states"]:
                return state_key, name
    except requests.RequestException as e:
        logger.warning("Nominatim geocode failed: %s", e)
    return None


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


_INVALID_LOCATION = {
    "en": "Invalid location. Please enter a valid city.",
    "hi": "स्थान मान्य नहीं है। कृपया सही शहर दर्ज करें।",
}


def _build_response(state_key: str, city_display: str, language: str,
                    notice: str = "") -> dict:
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


def _invalid_location_response(language: str) -> dict:
    """Strict error response when location can't be resolved.
    Per product spec we do NOT show automatic state-level fallback."""
    lang = _pick_lang(language)
    return {"ok": False, "error": _INVALID_LOCATION[lang]}


def region_soil_advice(city: Optional[str] = None,
                       lat=None, lon=None,
                       language: str = "hi") -> dict:
    """Main entry point. Returns matched state advice when the city or GPS
    coordinates resolve to a known Indian state. If we can't resolve the
    location, returns a clean ok:false error so the UI can prompt the
    farmer to re-enter a valid city — no silent state-level fallback."""

    # 1) City path
    if city and str(city).strip():
        city_str = city.strip()
        state_key = _resolve_city_to_state(city_str)
        if state_key and state_key in _DATA["states"]:
            return _build_response(state_key, city_str, language, notice="")

        # 1a) Try OpenWeather geocoding for any Indian city not in our list
        geo_hit = _geocode_city_to_state(city_str)
        if geo_hit:
            gk, resolved_name = geo_hit
            return _build_response(gk, resolved_name or city_str,
                                   language, notice="")

        # 1b) Try OpenStreetMap (Nominatim) — covers districts like Wayanad
        nom_hit = _nominatim_city_to_state(city_str)
        if nom_hit:
            gk, resolved_name = nom_hit
            return _build_response(gk, resolved_name or city_str,
                                   language, notice="")

        # 1c) Try fuzzy match for typos against our static city list
        fuzzy_key = _fuzzy_city_match(_norm(city_str))
        if fuzzy_key and fuzzy_key in _DATA["states"]:
            return _build_response(fuzzy_key, city_str, language, notice="")

        # 1c) Unknown city → try GPS if also provided, else error out cleanly
        if lat is not None and lon is not None:
            geo = _reverse_geocode_state(lat, lon)
            if geo:
                state_raw, city_name = geo
                gk = _DATA["state_aliases"].get(_norm(state_raw))
                if gk and gk in _DATA["states"]:
                    return _build_response(gk, city_name or city_str,
                                           language, notice="")
        return _invalid_location_response(language)

    # 2) GPS-only path
    if lat is not None and lon is not None:
        geo = _reverse_geocode_state(lat, lon)
        if geo:
            state_raw, city_name = geo
            state_key = _DATA["state_aliases"].get(_norm(state_raw))
            if state_key and state_key in _DATA["states"]:
                return _build_response(state_key, city_name or state_raw,
                                       language, notice="")
        return _invalid_location_response(language)

    # 3) No input at all
    return _invalid_location_response(language)
