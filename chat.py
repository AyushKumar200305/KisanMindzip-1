import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

# Store conversation history for memory
conversation_history = []

SYSTEM_PROMPT = """
Tu KisanMind ka AI assistant hai — ek expert Kisan Sevak.

Tera kaam hai Indian farmers ki madad karna. Tu sirf farming related topics pe baat karega.

Rules:
- Hamesha Hindi ya Hinglish mein jawab de
- Simple bhasha use kar — jaise ek gaon ka samajhdar dost bolta hai
- Short rakho — max 80-100 words per reply
- Sirf in topics pe baat kar:
  * Fasal/crop advice
  * Mitti (soil) ki dekhbhal
  * Paani/irrigation tips
  * Khaad (fertilizer) suggestions
  * Mausam aur fasal ka sambandh
  * Kisan government schemes (PM-KISAN, MSP, etc.)
  * Fasal ki bimari (crop disease) aur ilaaj
- Agar koi farming se bahar ka sawaal pooche, politely mana kar do
"""

def chat_with_kisan(user_message):
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Call Groq with full history for memory
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT}
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