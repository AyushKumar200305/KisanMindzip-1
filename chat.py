import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

# Store conversation history for memory — capped to avoid unbounded growth
conversation_history = []
MAX_HISTORY_TURNS = 10  # keep last 10 user+assistant pairs = 20 messages

# Hard limit so a slow Groq call never freezes the UI
GROQ_TIMEOUT_SEC = 15

SYSTEM_PROMPT_HI = """
तू KisanMind का AI सहायक है — एक एक्सपर्ट कृषि सलाहकार, भारतीय किसानों के लिए।
सिर्फ़ खेती से जुड़ी बात कर: फसल सलाह, मिट्टी, सिंचाई का सही समय, फसल का अंतर (spacing),
खाद की मात्रा, कीटनाशक/फफूंदनाशक की सुरक्षित खुराक, मौसम, सरकारी योजनाएँ (PM-KISAN, MSP),
और रोग व उपचार। खेती से बाहर का सवाल हो तो विनम्रता से मना कर दे।

सुरक्षा नियम (बहुत ज़रूरी):
- कीटनाशक/फफूंदनाशक की सुरक्षित सीमा बताओ — आमतौर पर 1–2 ml प्रति लीटर पानी।
- कभी भी ख़तरनाक या ज़्यादा खुराक मत बताओ।
- किसी कंपनी/ब्रांड का नाम मत लो — सिर्फ़ active ingredient या साधारण नाम बताओ।
- सलाह आसान और सुरक्षित हो — सिंचाई का समय, फसल अंतर, खाद, मिट्टी की देखभाल।
- अंत में हमेशा जोड़: "उपयोग से पहले अपने स्थानीय कृषि विभाग की सलाह ज़रूर लें।"

भाषा नियम (अनिवार्य):
- सिर्फ़ हिंदी (देवनागरी) में जवाब दे — जैसे: फसल, मिट्टी, खाद।
- Hinglish या Roman लिपि बिल्कुल मत इस्तेमाल कर।
- सरल, गाँव-समझ हिंदी। ज़्यादा से ज़्यादा 120 शब्द — और ज़रूरी हो तो जवाब पूरा करें, बीच में मत काटें।
"""

SYSTEM_PROMPT_EN = """
You are KisanMind's AI assistant — an expert agriculture advisor for Indian farmers.
Give simple, safe, practical advice on: crop selection, soil health, irrigation timing,
crop spacing, fertilizer guidance, safe pesticide/fungicide ranges, weather,
Indian government schemes (PM-KISAN, MSP), and crop diseases & treatment.
Politely refuse any non-farming question.

SAFETY RULES (MUST FOLLOW):
- Always state safe ranges for pesticides/fungicides — typically 1–2 ml per liter of water.
- Never recommend dangerous or excessive doses.
- Never mention specific brand names — refer only to the active ingredient or generic name.
- Keep advice simple and safe: irrigation timing, spacing, fertilizer, soil care.
- Always end the reply with: "Follow local agricultural guidelines before use."

LANGUAGE RULE (MUST FOLLOW):
- Reply ONLY in clear, simple English.
- Do NOT use Hindi, Hinglish, or any non-English words.
- Keep replies short — max 120 words. If a complete answer needs more, finish the sentence — never cut off mid-thought.
"""

# ─────────────────────────────────────────
# Safe fallback answers — used ONLY when the Groq API is unreachable.
# Keeps the demo alive instead of returning an empty/error reply.
# ─────────────────────────────────────────
_FALLBACK_HI = (
    "अभी AI सेवा थोड़ी धीमी है, फिर भी कुछ सुरक्षित सामान्य सलाह:\n"
    "• कीटनाशक/फफूंदनाशक: 1–2 ml प्रति लीटर पानी से शुरू करें।\n"
    "• सिंचाई: सुबह जल्दी या शाम को करें ताकि पानी कम वाष्पित हो।\n"
    "• खाद: मिट्टी की जाँच (Soil Health Card) के बाद ही दें।\n"
    "• रोग दिखे तो पहले प्रभावित पत्ती हटाएँ, फिर इलाज करें।\n"
    "उपयोग से पहले अपने स्थानीय कृषि विभाग की सलाह ज़रूर लें।"
)

_FALLBACK_EN = (
    "The AI service is a bit slow right now, but here is some safe general advice:\n"
    "• Pesticides/fungicides: start at 1–2 ml per liter of water.\n"
    "• Irrigate early morning or evening to reduce evaporation.\n"
    "• Apply fertilizer only after a Soil Health Card test.\n"
    "• If disease appears, first remove the affected leaves, then treat.\n"
    "Follow local agricultural guidelines before use."
)


def _safe_fallback(language):
    return _FALLBACK_EN if (language or "").lower().startswith("en") else _FALLBACK_HI

def _lang_rule(language):
    if (language or "").lower().startswith("en"):
        return ("\nReminder: Reply ONLY in clear, simple English. "
                "No Hindi, no Hinglish.")
    return ("\nReminder: Reply ONLY in Hindi (Devanagari script). "
            "No Hinglish, no English.")


def chat_with_kisan(user_message, language="hi"):
    if not user_message or not user_message.strip():
        return "Please send a message." if (language or "").lower().startswith("en") else "कृपया कोई संदेश भेजें।"

    conversation_history.append({
        "role": "user",
        "content": user_message.strip()
    })

    # Trim history to keep only the last MAX_HISTORY_TURNS turns
    if len(conversation_history) > MAX_HISTORY_TURNS * 2:
        del conversation_history[:-MAX_HISTORY_TURNS * 2]

    base = SYSTEM_PROMPT_EN if (language or "").lower().startswith("en") else SYSTEM_PROMPT_HI
    sys_prompt = base + _lang_rule(language)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": sys_prompt}
            ] + conversation_history,
            max_tokens=600,
            temperature=0.7,
            timeout=GROQ_TIMEOUT_SEC,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        # Don't crash the demo — drop the unanswered user turn and serve a safe canned reply.
        logger.warning("Groq chat call failed, returning safe fallback: %s", e)
        conversation_history.pop()  # remove the user message we just added
        return _safe_fallback(language)

    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    return reply

def reset_chat():
    """Clear conversation history for new session"""
    conversation_history.clear()

# Test it
if __name__ == "__main__":
    print("🌾 KisanMind Chatbot — Type 'quit' to exit, 'reset' to clear history\n")
    
    while True:
        user_input = input("Aap: ")
        
        if user_input.lower() == "quit":
            break
        elif user_input.lower() == "reset":
            reset_chat()
            print("Bot: Nayi baat shuru karte hain! Kya poochna hai?\n")
            continue
            
        response = chat_with_kisan(user_input)
        print(f"KisanBot: {response}\n")