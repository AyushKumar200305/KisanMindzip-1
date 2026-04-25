import json
import os
import re
from pathlib import Path

from groq import Groq

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


# Plain-text fallback summary for the LLM (only used when the JSON
# search returns nothing). Kept short so the LLM can still help.
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
# JSON search helpers
# ─────────────────────────────────────────
def _normalize(text):
    if not text:
        return ""
    text = text.lower()
    # Strip punctuation but keep Devanagari characters intact
    return re.sub(r"[^\w\u0900-\u097F\s]", " ", text)


def _score_scheme(scheme, query_norm):
    """Return a relevance score for this scheme vs the user query."""
    score = 0
    for kw in scheme.get("keywords", []):
        kw_n = _normalize(kw).strip()
        if not kw_n:
            continue
        # Whole-word match for short keywords; substring otherwise
        if len(kw_n) <= 4:
            if re.search(r"\b" + re.escape(kw_n) + r"\b", query_norm):
                score += 3
        elif kw_n in query_norm:
            # Longer / multi-word phrases are stronger signals
            score += 5 if " " in kw_n else 4
    return score


def _find_matching_schemes(query, limit=3):
    """Return list of schemes (highest score first) matching the query.
       Empty list means no confident match — caller should fall back to AI."""
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
# Formatters (no LLM — verified text only)
# ─────────────────────────────────────────
def _labels(language):
    if (language or "").lower().startswith("en"):
        return {
            "eligibility": "Eligibility",
            "benefits": "Benefits",
            "steps": "How to Apply",
            "source": "Source: verified KisanMind database",
        }
    return {
        "eligibility": "पात्रता",
        "benefits": "लाभ",
        "steps": "आवेदन कैसे करें",
        "source": "स्रोत: KisanMind सत्यापित डेटाबेस",
    }


def _format_scheme(scheme, language):
    lang = "en" if (language or "").lower().startswith("en") else "hi"
    data = scheme.get(lang) or scheme.get("en") or {}
    lab = _labels(language)

    def _bullets(items):
        return "\n".join(f"• {it}" for it in (items or []))

    def _steps(items):
        return "\n".join(f"{i+1}. {it}" for i, it in enumerate(items or []))

    return (
        f"📌 {data.get('name', '').strip()}\n\n"
        f"✅ {lab['eligibility']}:\n{_bullets(data.get('eligibility'))}\n\n"
        f"🎁 {lab['benefits']}:\n{_bullets(data.get('benefits'))}\n\n"
        f"📝 {lab['steps']}:\n{_steps(data.get('steps'))}"
    )


def _format_matches(matches, language):
    lab = _labels(language)
    blocks = [_format_scheme(s, language) for s in matches]
    separator = "\n\n" + ("─" * 30) + "\n\n"
    return separator.join(blocks) + f"\n\n— {lab['source']}"


# ─────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────
def sarkari_yojana_agent(query, state=None, language="hi"):
    """
    Answer farmer questions about government schemes.

    Strategy:
      1. Try to match the query against the verified schemes.json database.
         If one or more schemes match, return their structured info directly
         (no LLM, so no hallucination).
      2. Otherwise fall back to the existing Groq-based advisor using the
         short SCHEMES_DATABASE summary as context.
    """
    matches = _find_matching_schemes(query)

    if matches:
        return {
            "query": query,
            "state": state if state else "Not specified",
            "source": "database",
            "matched_schemes": [m["id"] for m in matches],
            "agent_advice": _format_matches(matches, language),
        }

    # ─── AI fallback (existing logic, unchanged in spirit) ───
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
    - <point 2>
    Benefits:
    - <point 1>
    - <point 2>
    Steps:
    1. <step 1>
    2. <step 2>

    Maximum 180 words. Use simple language.
    """ + _lang_rule(language)

    sys_msg = (
        "You are an expert Indian government-schemes advisor. Reply in clear, simple English. "
        "Never invent schemes, amounts or websites. If unsure, say so."
        if (language or "").lower().startswith("en") else
        "Tu Bharat ki sarkari yojanaon ka expert salahkar hai. Shuddh Hindi (Devanagari) mein jawab de. "
        "Kabhi bhi koi nayi yojana, raashi ya website mat banao. Agar pakka nahi pata to spasht keh do."
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
    )

    advice = response.choices[0].message.content

    return {
        "query": query,
        "state": state if state else "Not specified",
        "source": "ai_fallback",
        "matched_schemes": [],
        "agent_advice": advice,
    }


# Test
if __name__ == "__main__":
    print("🏛️ KisanMind — Sarkari Yojana Agent\n")

    state = input("Aapka state (optional, Enter skip): ").strip()
    state = state if state else None

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
