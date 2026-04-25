import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

# Store conversation history for memory
conversation_history = []

SYSTEM_PROMPT_HI = """
Tu KisanMind ka AI assistant hai — ek expert Kisan Sevak.
Tera kaam hai Indian farmers ki madad karna. Tu sirf farming-related topics pe baat karega:
fasal advice, mitti, paani/irrigation, khaad, mausam, government schemes (PM-KISAN, MSP),
aur fasal ki bimari aur ilaaj. Agar koi farming se bahar ka sawaal pooche, politely mana kar do.

LANGUAGE RULE (MUST FOLLOW):
- Reply ONLY in Hindi using Devanagari script (e.g. नमस्ते, फसल, मिट्टी).
- Do NOT use Hinglish or Roman/English transliteration.
- Use simple, village-friendly Hindi. Max 80-100 words.
"""

SYSTEM_PROMPT_EN = """
You are KisanMind's AI assistant — an expert farm advisor for Indian farmers.
Only discuss farming topics: crop advice, soil health, irrigation, fertilizers, weather,
Indian government schemes (PM-KISAN, MSP, etc.), and crop diseases / treatment.
Politely refuse any non-farming question.

LANGUAGE RULE (MUST FOLLOW):
- Reply ONLY in clear, simple English.
- Do NOT use Hindi, Hinglish, or any non-English words.
- Keep replies short — max 80-100 words.
"""

def _lang_rule(language):
    if (language or "").lower().startswith("en"):
        return ("\nReminder: Reply ONLY in clear, simple English. "
                "No Hindi, no Hinglish.")
    return ("\nReminder: Reply ONLY in Hindi (Devanagari script). "
            "No Hinglish, no English.")


def chat_with_kisan(user_message, language="hi"):
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    base = SYSTEM_PROMPT_EN if (language or "").lower().startswith("en") else SYSTEM_PROMPT_HI
    sys_prompt = base + _lang_rule(language)

    # Call Groq with full history for memory
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": sys_prompt}
        ] + conversation_history,
        max_tokens=200
    )
    
    # Get reply
    reply = response.choices[0].message.content
    
    # Add assistant reply to history
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