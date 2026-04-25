import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

# Database of major schemes
SCHEMES_DATABASE = """
1. PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)
   - ₹6000/year direct to farmer's bank account (3 installments of ₹2000)
   - Eligibility: Small/marginal farmers with less than 2 hectare land
   - Apply: pmkisan.gov.in or nearest CSC center

2. PM Fasal Bima Yojana (PMFBY)
   - Crop insurance against natural disasters, pests, diseases
   - Premium: 2% for Kharif, 1.5% for Rabi crops
   - Apply: nearest bank or insurance company

3. Kisan Credit Card (KCC)
   - Low interest loan (4% per year) for farming needs
   - Up to ₹3 lakh without collateral
   - Apply: nearest bank branch

4. PM Krishi Sinchai Yojana
   - Subsidy on drip/sprinkler irrigation systems (up to 55-90%)
   - Apply: state agriculture department

5. Soil Health Card Scheme
   - Free soil testing and crop recommendations
   - Apply: nearest Krishi Vigyan Kendra (KVK)

6. eNAM (National Agriculture Market)
   - Online mandi platform — sell crops at best national price
   - Register: enam.gov.in

7. Kisan Vikas Patra
   - Safe investment scheme — money doubles in 115 months
   - Available at post offices

8. MNREGA for Farmers
   - 100 days guaranteed wage work
   - Also covers farm pond construction, land leveling

9. PM Kisan Mandhan Yojana
   - Pension scheme for farmers — ₹3000/month after age 60
   - Premium: ₹55-200/month based on age
   - Apply: CSC center or pmkmy.gov.in

10. Paramparagat Krishi Vikas Yojana (PKVY)
    - Support for organic farming — ₹50,000/hectare over 3 years
    - Apply: state agriculture department
"""

def _lang_rule(language):
    if (language or "").lower().startswith("en"):
        return ("\n\nIMPORTANT: Reply ONLY in clear, simple English. "
                "Do NOT use Hindi or Hinglish words.")
    return ("\n\nIMPORTANT: Reply ONLY in Hindi (Devanagari script). "
            "Use simple, village-friendly Hindi.")


def sarkari_yojana_agent(query, state=None, language="hi"):
    """
    Answer farmer questions about government schemes
    query: farmer's question about schemes
    state: optional state for state-specific schemes
    """
    
    state_info = f"Farmer {state} se hai." if state else ""
    
    prompt = f"""
    Tu ek expert Government Schemes Advisor hai jo farmers ko sarkari yojanaon ke baare mein batata hai.
    
    {state_info}
    
    Yeh major central government schemes hain:
    {SCHEMES_DATABASE}
    
    Farmer ka sawaal: {query}
    
    Hindi/Hinglish mein jawab do:
    
    1. Relevant Scheme(s):
       - Konsi yojana farmer ke liye best hai
       - Kya milega (amount/benefit)
    
    2. Eligibility:
       - Kaun apply kar sakta hai
    
    3. Kaise Apply Karein:
       - Simple steps mein batao
       - Website ya center ka naam
    
    Max 150 words. Bilkul simple bhasha.
    """ + _lang_rule(language)

    sys_msg = ("You are an expert Indian government-schemes advisor. Always reply in clear, simple English."
               if (language or "").lower().startswith("en") else
               "Tu ek expert Government Schemes Advisor hai. Farmers ko shuddh Hindi (Devanagari) mein sarkari yojanaon ki sahi jaankari deta hai.")

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": sys_msg
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=350
    )
    
    advice = response.choices[0].message.content
    
    return {
        "query": query,
        "state": state if state else "Not specified",
        "agent_advice": advice
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
        print(f"\nJawaab:\n{result['agent_advice']}")
        print("=" * 50 + "\n")