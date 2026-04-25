import os
import requests
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")
DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "")

def get_mandi_prices(commodity, state):
    """Fetch live mandi prices from data.gov.in API"""
    try:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": "5",
            "filters[commodity]": commodity,
            "filters[state]": state
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data.get("records", [])
    except Exception as e:
        return []

def mandi_bhav_agent(commodity, state):
    """
    Get mandi prices and give AI-powered advice
    commodity: e.g. 'Wheat', 'Rice', 'Tomato'
    state: e.g. 'Uttar Pradesh', 'Punjab', 'Haryana'
    """
    
    # Step 1: Fetch live prices
    records = get_mandi_prices(commodity, state)
    
    # Step 2: Format price data
    if records:
        price_text = ""
        for r in records:
            price_text += f"""
            - Mandi: {r.get('market', 'N/A')} ({r.get('district', 'N/A')})
              Min: ₹{r.get('min_price', 'N/A')} | Max: ₹{r.get('max_price', 'N/A')} | Modal: ₹{r.get('modal_price', 'N/A')} per quintal
              Date: {r.get('arrival_date', 'N/A')}
            """
    else:
        price_text = "Live data abhi available nahi hai."
    
    # Step 3: Ask Groq for advice
    prompt = f"""
    Farmer {state} mein {commodity} bechna chahta hai.
    
    Aaj ke mandi bhav:
    {price_text}
    
    Farmer ko Hindi/Hinglish mein batao:
    
    1. Bhav Summary:
       - Sabse achha bhav kahan mil raha hai
       - Average price kya hai
    
    2. Bechne ki Salah:
       - Kya abhi bechna sahi hai ya wait karein
       - Kaunsi mandi mein bechein
    
    3. Ek Line Tip:
       - Quick farming business advice
    
    Max 120 words. Simple bhasha.
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "Tu ek expert Mandi Advisor hai jo farmers ko best price aur selling strategy batata hai Hindi/Hinglish mein."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300
    )
    
    advice = response.choices[0].message.content
    
    return {
        "commodity": commodity,
        "state": state,
        "live_prices": records,
        "agent_advice": advice
    }


# Test
if __name__ == "__main__":
    print("💰 KisanMind — Mandi Bhav Agent\n")
    
    commodity = input("Fasal ka naam (e.g. Wheat, Rice, Tomato): ").strip()
    state = input("State ka naam (e.g. Uttar Pradesh, Punjab): ").strip()
    
    print("\nMandi bhav fetch ho raha hai...\n")
    
    result = mandi_bhav_agent(commodity, state)
    
    print("=" * 50)
    print(f"Fasal: {result['commodity']} | State: {result['state']}")
    print("=" * 50)
    if result['live_prices']:
        print("\nLive Mandi Prices:")
        for r in result['live_prices']:
            print(f"  • {r.get('market')} — ₹{r.get('modal_price')} per quintal")
    print(f"\nAgent Advice:\n{result['agent_advice']}")
    print("=" * 50)