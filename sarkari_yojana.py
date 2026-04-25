import json
import logging
import os
import re
from pathlib import Path

from groq import Groq

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

# ─────────────────────────────────────────
# Load the verified, structured schemes DB
# ─────────────────────────────────────────
_SCHEMES_PATH = Path(__file__).with_name("schemes.json")
try:
    with _SCHEMES_PATH.open("r", encoding="utf-8") as _f:
        _SCHEMES = json.load(_f).get("schemes", [])
except Exception:
    _SCHEMES = []

# Quick lookup index
_SCHEMES_BY_ID = {s["id"]: s for s in _SCHEMES}


# Plain-text fallback summary (only used when both Groq and keyword search fail)
SCHEMES_DATABASE = """
1. PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)
   - ₹6000/year direct to farmer's bank account (3 installments of ₹2000)
   - Eligibility: Small/marginal farmers with cultivable land
   - Apply: pmkisan.gov.in or nearest CSC center

2. PM Fasal Bima Yojana (PMFBY)
   - Crop insurance against natural disasters, pests, diseases
   - Premium: 2% for Kharif, 1.5% for Rabi crops
   - Apply: nearest bank or insurance company

3. Kisan Credit Card (KCC)
   - Low interest crop loan (4% with timely repayment subvention)
   - Up to ₹1.6 lakh without collateral
   - Apply: nearest bank branch

4. PM Krishi Sinchayee Yojana (Per Drop More Crop)
   - Subsidy on drip/sprinkler irrigation systems (45–55% typically)
   - Apply: state agriculture/horticulture department

5. Soil Health Card Scheme
   - Free soil testing and crop-wise fertilizer recommendations
   - Apply: nearest Krishi Vigyan Kendra (KVK)

6. eNAM (National Agriculture Market)
   - Online mandi platform — sell crops at best national price
   - Register: enam.gov.in

7. Kisan Vikas Patra (post office) — money doubles in 115 months.

8. MGNREGA — 100 days guaranteed wage work for rural households,
   plus farm-pond / well construction on small farmer's land.

9. PM Kisan Maan-Dhan Yojana — pension of ₹3000/month after age 60
   for small/marginal farmers (joining age 18–40).

10. Paramparagat Krishi Vikas Yojana (PKVY)
    - Support for cluster-based organic farming — about ₹50,000/hectare over 3 years
    - Apply: state agriculture department
"""


def _lang_rule(language):
    if (language or "").lower().startswith("en"):
        return ("\n\nIMPORTANT: Reply ONLY in clear, simple English. "
                "Do NOT use Hindi or Hinglish words.")
    return ("\n\nIMPORTANT: Reply ONLY in Hindi (Devanagari script). "
            "Use simple, village-friendly Hindi.")


# ─────────────────────────────────────────
# Local keyword search (used as fallback + ranker)
# ─────────────────────────────────────────
def _normalize(text):
    if not text:
        return ""
    text = text.lower()
    return re.sub(r"[^\w\u0900-\u097F\s]", " ", text)


def _score_scheme(scheme, query_norm):
    score = 0
    for kw in scheme.get("keywords", []):
        kw_n = _normalize(kw).strip()
        if not kw_n:
            continue
        if len(kw_n) <= 4:
            if re.search(r"\b" + re.escape(kw_n) + r"\b", query_norm):
                score += 3
        elif kw_n in query_norm:
            score += 5 if " " in kw_n else 4
    return score


def _keyword_search(query, limit=5):
    """Return list of schemes (highest score first) from local keyword match."""
    if not _SCHEMES or not query:
        return []
    q_norm = _normalize(query)
    scored = []
    for s in _SCHEMES:
        sc = _score_scheme(s, q_norm)
        if sc > 0:
            scored.append((sc, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:limit]]


# ─────────────────────────────────────────
# Groq-powered intent extractor → scheme IDs
# ─────────────────────────────────────────
def _scheme_catalog_for_prompt():
    """Compact catalog the LLM uses to choose IDs."""
    lines = []
    for s in _SCHEMES:
        en = s.get("en", {})
        kws = ", ".join(s.get("keywords", [])[:8])
        lines.append(f"- id: {s['id']} | name: {en.get('name','')} | keywords: {kws}")
    return "\n".join(lines)


def _groq_match_scheme_ids(query, max_ids=5):
    """
    Ask Groq to map the user's free-text query to up to `max_ids` scheme ids
    from the local catalog. Returns a list of valid ids in priority order.
    Returns [] on any failure (caller handles fallback).
    """
    if not _SCHEMES:
        return []
    try:
        catalog = _scheme_catalog_for_prompt()
        sys_msg = (
            "You are a precise classifier for Indian government farming schemes. "
            "You will be given a user's question and a fixed catalog of scheme IDs. "
            "Pick the IDs from the catalog that best answer the question, in order "
            "of relevance. Respond with ONLY a JSON object of the form "
            '{"ids": ["id1", "id2", ...]} — no prose, no markdown. '
            "Only use IDs that appear in the catalog. If nothing fits, return "
            '{"ids": []}.'
        )
        user_msg = (
            f"Catalog (id | name | keywords):\n{catalog}\n\n"
            f"User question: {query}\n\n"
            f"Return at most {max_ids} ids, most relevant first."
        )
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=120,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        parsed = json.loads(raw)
        ids = parsed.get("ids") or []
        # Keep only IDs that exist in our catalog, preserve order, dedupe
        valid, seen = [], set()
        for i in ids:
            if isinstance(i, str) and i in _SCHEMES_BY_ID and i not in seen:
                valid.append(i)
                seen.add(i)
            if len(valid) >= max_ids:
                break
        return valid
    except Exception:
        logger.exception("Groq intent extraction failed; using keyword fallback")
        return []


def _resolve_top_schemes(query, limit=5):
    """
    Best-effort matcher:
      1. Try Groq intent extraction (semantic understanding).
      2. If empty, fall back to local keyword search.
    Returns (matches, source) where source is 'groq_match' or 'keyword_search'.
    """
    ids = _groq_match_scheme_ids(query, max_ids=limit)
    if ids:
        return ([_SCHEMES_BY_ID[i] for i in ids if i in _SCHEMES_BY_ID],
                "groq_match")
    return _keyword_search(query, limit=limit), "keyword_search"


# ─────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────
def _labels(language):
    if (language or "").lower().startswith("en"):
        return {
            "eligibility": "Eligibility",
            "benefits": "Benefits",
            "steps": "How to Apply",
            "source": "Source: verified KisanMind database",
            "apply": "Apply / Learn More",
        }
    return {
        "eligibility": "पात्रता",
        "benefits": "लाभ",
        "steps": "आवेदन कैसे करें",
        "source": "स्रोत: KisanMind सत्यापित डेटाबेस",
        "apply": "आवेदन करें / और जानें",
    }


def _short_description(localized, max_chars=180):
    """Build a one-line description from benefits (preferred) or eligibility."""
    parts = localized.get("benefits") or localized.get("eligibility") or []
    if not parts:
        return ""
    desc = parts[0].strip()
    if len(desc) > max_chars:
        desc = desc[: max_chars - 1].rstrip() + "…"
    return desc


def _structured_scheme(scheme, language):
    """Compact card-friendly dict for the frontend."""
    lang = "en" if (language or "").lower().startswith("en") else "hi"
    data = scheme.get(lang) or scheme.get("en") or {}
    return {
        "id": scheme.get("id"),
        "name": data.get("name", "").strip(),
        "description": _short_description(data),
        "eligibility": data.get("eligibility", []),
        "benefits": data.get("benefits", []),
        "steps": data.get("steps", []),
        "link": scheme.get("link", ""),
    }


def _format_scheme_text(scheme, language):
    """Plain-text block — kept for backward compat with existing renderer."""
    lang = "en" if (language or "").lower().startswith("en") else "hi"
    data = scheme.get(lang) or scheme.get("en") or {}
    lab = _labels(language)

    def _bullets(items):
        return "\n".join(f"• {it}" for it in (items or []))

    def _steps(items):
        return "\n".join(f"{i+1}. {it}" for i, it in enumerate(items or []))

    link = scheme.get("link", "")
    link_line = f"\n\n🔗 {lab['apply']}: {link}" if link else ""

    return (
        f"📌 {data.get('name', '').strip()}\n\n"
        f"✅ {lab['eligibility']}:\n{_bullets(data.get('eligibility'))}\n\n"
        f"🎁 {lab['benefits']}:\n{_bullets(data.get('benefits'))}\n\n"
        f"📝 {lab['steps']}:\n{_steps(data.get('steps'))}"
        f"{link_line}"
    )


def _format_matches_text(matches, language):
    lab = _labels(language)
    blocks = [_format_scheme_text(s, language) for s in matches]
    separator = "\n\n" + ("─" * 30) + "\n\n"
    return separator.join(blocks) + f"\n\n— {lab['source']}"


# ─────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────
def sarkari_yojana_agent(query, state=None, language="hi"):
    """
    Smart scheme finder.

    Flow:
      1. Send the user's query to Groq → get a ranked list of catalog IDs.
      2. Fall back to local keyword search if Groq is unavailable / empty.
      3. Return a structured `schemes` array (cards with link), plus a
         human-readable `agent_advice` text for the legacy renderer.
      4. If nothing matches at all, run the existing Groq advisor on
         the SCHEMES_DATABASE summary so the user always gets an answer.
    """
    matches, source = _resolve_top_schemes(query, limit=5)

    if matches:
        structured = [_structured_scheme(s, language) for s in matches]
        return {
            "query": query,
            "state": state if state else "Not specified",
            "source": source,
            "matched_schemes": [m["id"] for m in matches],
            "schemes": structured,
            "agent_advice": _format_matches_text(matches, language),
        }

    # ─── No structured match → freeform Groq advisor (existing behaviour) ───
    state_info = f"Farmer is from {state}." if state else ""
    prompt = f"""
    You are an expert advisor on Indian government schemes for farmers.

    {state_info}

    Use ONLY the verified central government schemes listed below as your reference.
    Do NOT invent schemes, amounts, websites, deadlines or eligibility rules that
    are not present here. If the answer is not in this list, say so honestly and
    suggest the farmer visit their nearest Krishi Vigyan Kendra (KVK).

    Reference schemes:
    {SCHEMES_DATABASE}

    Farmer's question: {query}

    Reply in this exact structure:

    Name: <scheme name>
    Eligibility:
    - <point 1>
    Benefits:
    - <point 1>
    Steps:
    1. <step 1>

    Maximum 180 words. Use simple language.
    """ + _lang_rule(language)

    sys_msg = (
        "You are an expert Indian government-schemes advisor. Reply in clear, simple English. "
        "Never invent schemes, amounts or websites. If unsure, say so."
        if (language or "").lower().startswith("en") else
        "Tu Bharat ki sarkari yojanaon ka expert salahkar hai. Shuddh Hindi (Devanagari) mein jawab de. "
        "Kabhi bhi koi nayi yojana, raashi ya website mat banao. Agar pakka nahi pata to spasht keh do."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
        )
        advice = response.choices[0].message.content
    except Exception:
        logger.exception("Groq advisor fallback failed")
        advice = (
            "Sorry, the AI advisor is unavailable right now. Please try again, "
            "or visit your nearest Krishi Vigyan Kendra (KVK) for help."
            if (language or "").lower().startswith("en") else
            "क्षमा करें, AI सलाहकार अभी उपलब्ध नहीं है। कृपया फिर से कोशिश करें "
            "या मदद के लिए नज़दीकी कृषि विज्ञान केंद्र (KVK) जाएँ।"
        )

    return {
        "query": query,
        "state": state if state else "Not specified",
        "source": "ai_fallback",
        "matched_schemes": [],
        "schemes": [],
        "agent_advice": advice,
    }


# Test
if __name__ == "__main__":
    print("🏛️ KisanMind — Sarkari Yojana Agent\n")
    state = input("Aapka state (optional, Enter skip): ").strip() or None
    print("\nType 'quit' to exit\n")
    while True:
        query = input("Aapka sawaal: ").strip()
        if query.lower() == "quit":
            break
        print("\nJaankari dhundhi ja rahi hai...\n")
        result = sarkari_yojana_agent(query, state)
        print("=" * 50)
        print(f"\nSource: {result['source']}  Matched: {result['matched_schemes']}")
        print(f"\nJawaab:\n{result['agent_advice']}")
        print("=" * 50 + "\n")
