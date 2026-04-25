"""
Find the nearest mandis to a user's GPS location, fetch live prices from
data.gov.in (with graceful fallback), and produce structured output for the UI.

Public function:
    get_nearest_mandis(commodity, lat, lon, language="hi", limit=5)
        -> dict with keys:
            ok, commodity, language, user_location,
            nearest_mandis: [ {market, district, state, distance_km,
                               modal_price, min_price, max_price,
                               currency, source, arrival_date} ],
            best_mandi, average_price, advice (bilingual fields),
            chart: {labels, modal_prices, min_prices, max_prices},
            data_source, fallback_used
"""
from __future__ import annotations

import os
import math
import time
import logging
import random
import requests

from mandi_cities import MANDI_CITIES

logger = logging.getLogger(__name__)

DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "")
DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

# Realistic fallback modal prices in ₹/quintal (used only when live API fails).
_FALLBACK_PRICE_BAND = {
    "wheat":     (2050, 2400),
    "rice":      (2200, 2900),
    "paddy":     (1900, 2400),
    "tomato":    (1500, 2800),
    "onion":     (1400, 2600),
    "potato":    (900,  1700),
    "cotton":    (5500, 7100),
    "maize":     (1700, 2200),
    "soybean":   (3800, 4900),
    "soyabean":  (3800, 4900),
    "mustard":   (4600, 5800),
    "groundnut": (5500, 7000),
    "bajra":     (1900, 2400),
    "jowar":     (2500, 3200),
    "gram":      (4500, 5500),
    "sugarcane": (300,  380),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def _nearest_cities(lat: float, lon: float, limit: int = 8):
    """Return the closest cities from MANDI_CITIES, sorted by distance."""
    scored = []
    for market, district, state, mlat, mlon in MANDI_CITIES:
        d = _haversine_km(lat, lon, mlat, mlon)
        scored.append({
            "market": market,
            "district": district,
            "state": state,
            "lat": mlat,
            "lon": mlon,
            "distance_km": round(d, 1),
        })
    scored.sort(key=lambda c: c["distance_km"])
    return scored[:limit]


def _fetch_live_records(commodity: str, state: str | None, limit: int = 50):
    """Fetch live mandi records from data.gov.in. Returns [] on any failure."""
    if not DATA_GOV_API_KEY:
        return []
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": str(limit),
        "filters[commodity]": commodity,
    }
    if state:
        params["filters[state]"] = state
    try:
        r = requests.get(DATA_GOV_URL, params=params, timeout=10)
        if not r.ok:
            return []
        data = r.json() or {}
        return data.get("records", []) or []
    except requests.RequestException:
        return []
    except ValueError:
        return []


def _match_record_for_city(records: list, city: dict, used: set):
    """Return the live record best matching a candidate city (by district/market).
    Records already consumed (in `used`) are skipped so two nearby cities don't
    both grab the same row."""
    if not records:
        return None
    market_n = _norm(city["market"])
    district_n = _norm(city["district"])

    # Pass 1: exact district / market match
    for idx, r in enumerate(records):
        if idx in used:
            continue
        rm = _norm(r.get("market"))
        rd = _norm(r.get("district"))
        if not rm and not rd:
            continue
        if rm == market_n or rd == district_n:
            used.add(idx)
            return r

    # Pass 2: softer contains-match
    for idx, r in enumerate(records):
        if idx in used:
            continue
        rm = _norm(r.get("market"))
        rd = _norm(r.get("district"))
        if (market_n and (market_n in rm or rm in market_n)) or \
           (district_n and (district_n in rd or rd in district_n)):
            used.add(idx)
            return r
    return None


def _fallback_price(commodity: str, seed_key: str):
    """Deterministic-but-varied fallback prices so cards aren't identical."""
    band = _FALLBACK_PRICE_BAND.get(_norm(commodity), (1800, 2500))
    lo, hi = band
    rnd = random.Random(seed_key)
    modal = rnd.randint(lo, hi)
    spread = max(80, int((hi - lo) * 0.15))
    minp = max(50, modal - rnd.randint(40, spread))
    maxp = modal + rnd.randint(40, spread)
    return modal, minp, maxp


def _build_advice(commodity: str, mandis: list, language: str):
    """Bilingual selling advice. Both fields are returned so the UI can pick."""
    if not mandis:
        return {
            "best_mandi_name": "",
            "average_price": 0,
            "advice_en": "No nearby mandi data available right now. Please try again later.",
            "advice_hi": "अभी पास की मंडी का डेटा उपलब्ध नहीं है। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
        }

    modals = [m["modal_price"] for m in mandis if m.get("modal_price")]
    avg = round(sum(modals) / len(modals), 2) if modals else 0

    # Prefer live ('data.gov.in') prices when picking the best mandi —
    # estimated rows shouldn't outrank verified ones.
    live_only = [m for m in mandis if m.get("source") == "data.gov.in"]
    pool = live_only if live_only else mandis
    best = max(pool, key=lambda m: m.get("modal_price") or 0)
    nearest = mandis[0]

    best_name = best["market"]
    best_price = best["modal_price"]
    best_dist = best["distance_km"]

    if best is nearest:
        en_extra = f"It's also the nearest mandi ({best_dist} km), so transport cost stays low."
        hi_extra = f"यह सबसे पास की मंडी भी है ({best_dist} किमी), तो ढुलाई का खर्च कम रहेगा।"
    else:
        en_extra = (f"Best price is at {best_name} (₹{best_price}/quintal, {best_dist} km away). "
                    f"Compare transport cost with the nearest mandi {nearest['market']} ({nearest['distance_km']} km).")
        hi_extra = (f"सबसे अच्छा भाव {best_name} में है (₹{best_price}/क्विंटल, {best_dist} किमी दूर)। "
                    f"ढुलाई खर्च की तुलना सबसे पास की मंडी {nearest['market']} ({nearest['distance_km']} किमी) से कर लें।")

    if avg and best_price >= avg * 1.05:
        tip_en = "Prices look strong — selling soon is a good option."
        tip_hi = "कीमतें अच्छी दिख रही हैं — जल्दी बेचना सही रहेगा।"
    elif avg and best_price <= avg * 0.95:
        tip_en = "Prices are weak — wait a few days if you can store the crop safely."
        tip_hi = "कीमतें कमज़ोर हैं — यदि फसल सुरक्षित रख सकते हैं तो कुछ दिन रुकें।"
    else:
        tip_en = "Prices are average — sell if you need cash, otherwise watch the trend."
        tip_hi = "कीमतें सामान्य हैं — ज़रूरत हो तो बेचें, वरना भाव पर नज़र रखें।"

    advice_en = (f"Best mandi for {commodity}: {best_name} at ₹{best_price}/quintal. "
                 f"Average across nearby mandis is ₹{avg}/quintal. {en_extra} {tip_en}")
    advice_hi = (f"{commodity} के लिए सबसे अच्छी मंडी: {best_name} — ₹{best_price}/क्विंटल। "
                 f"पास की मंडियों का औसत भाव ₹{avg}/क्विंटल है। {hi_extra} {tip_hi}")

    return {
        "best_mandi_name": best_name,
        "best_mandi_price": best_price,
        "best_mandi_distance_km": best_dist,
        "average_price": avg,
        "advice_en": advice_en,
        "advice_hi": advice_hi,
        "tip_en": tip_en,
        "tip_hi": tip_hi,
    }


def get_nearest_mandis(commodity: str, lat: float, lon: float,
                       language: str = "hi", limit: int = 5) -> dict:
    """Main entry point used by the Flask route."""
    commodity = (commodity or "").strip()
    if not commodity:
        return {"ok": False, "error": "commodity is required"}
    try:
        lat = float(lat); lon = float(lon)
    except (TypeError, ValueError):
        return {"ok": False, "error": "valid lat/lon are required"}

    limit = max(3, min(int(limit or 5), 8))

    # 1. Find candidate nearest cities (a few extra so we can join with API rows).
    candidates = _nearest_cities(lat, lon, limit=limit + 3)
    nearest_state = candidates[0]["state"] if candidates else None

    # 2. Try live data for the user's state first, then a broader pull.
    live = _fetch_live_records(commodity, nearest_state, limit=80)
    if not live:
        live = _fetch_live_records(commodity, None, limit=80)

    fallback_used = False
    today = time.strftime("%Y-%m-%d")
    out_mandis = []
    used_records: set = set()
    for city in candidates:
        rec = _match_record_for_city(live, city, used_records) if live else None
        if rec:
            modal = _to_float(rec.get("modal_price"))
            minp = _to_float(rec.get("min_price"))
            maxp = _to_float(rec.get("max_price"))
            if not modal or modal <= 0:
                rec = None  # fall through to fallback
        if rec and modal and modal > 0:
            out_mandis.append({
                "market":       rec.get("market") or city["market"],
                "district":     rec.get("district") or city["district"],
                "state":        rec.get("state") or city["state"],
                "distance_km":  city["distance_km"],
                "modal_price":  round(modal, 2),
                "min_price":    round(minp, 2) if minp else None,
                "max_price":    round(maxp, 2) if maxp else None,
                "currency":     "INR",
                "unit":         "quintal",
                "arrival_date": rec.get("arrival_date") or today,
                "source":       "data.gov.in",
            })
        else:
            fallback_used = True
            seed_key = f"{commodity}|{city['market']}|{today}"
            modal, minp, maxp = _fallback_price(commodity, seed_key)
            out_mandis.append({
                "market":       city["market"],
                "district":     city["district"],
                "state":        city["state"],
                "distance_km":  city["distance_km"],
                "modal_price":  modal,
                "min_price":    minp,
                "max_price":    maxp,
                "currency":     "INR",
                "unit":         "quintal",
                "arrival_date": today,
                "source":       "estimated",
            })

    # 3. Already sorted by distance; trim to requested limit.
    out_mandis = out_mandis[:limit]

    # 4. Build advice + chart payload.
    advice = _build_advice(commodity, out_mandis, language)
    chart = {
        "labels":       [m["market"] for m in out_mandis],
        "modal_prices": [m["modal_price"] for m in out_mandis],
        "min_prices":   [m["min_price"]   for m in out_mandis],
        "max_prices":   [m["max_price"]   for m in out_mandis],
        "distances":    [m["distance_km"] for m in out_mandis],
    }

    data_source = "data.gov.in"
    if fallback_used and any(m["source"] == "data.gov.in" for m in out_mandis):
        data_source = "mixed (live + estimated)"
    elif fallback_used:
        data_source = "estimated (live data unavailable)"

    return {
        "ok": True,
        "commodity":      commodity,
        "language":       "en" if (language or "").lower().startswith("en") else "hi",
        "user_location":  {"lat": lat, "lon": lon, "state_guess": nearest_state},
        "nearest_mandis": out_mandis,
        "best_mandi":     advice.get("best_mandi_name", ""),
        "average_price":  advice.get("average_price", 0),
        "advice_en":      advice.get("advice_en", ""),
        "advice_hi":      advice.get("advice_hi", ""),
        "tip_en":         advice.get("tip_en", ""),
        "tip_hi":         advice.get("tip_hi", ""),
        "chart":          chart,
        "data_source":    data_source,
        "fallback_used":  fallback_used,
    }
