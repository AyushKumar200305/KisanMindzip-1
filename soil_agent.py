import os
from groq import Groq
from predict import predict_crop

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def soil_sense_agent(N, P, K, temperature, humidity, ph, rainfall):
    # Step 1: Get crop from ML model
    crop = predict_crop(N, P, K, temperature, humidity, ph, rainfall)
    
    # Step 2: Build prompt
    prompt = f"""
    Tu ek expert Kisan Sevak hai. Ek farmer ne apni mitti ki jaankari di hai:
    - Nitrogen (N): {N}
    - Phosphorus (P): {P}
    - Potassium (K): {K}
    - Temperature: {temperature}°C
    - Humidity: {humidity}%
    - Soil pH: {ph}
    - Rainfall: {rainfall}mm

    Hamare AI model ne suggest kiya hai ki is mitti mein: {crop} ugana best rahega.

    Ab farmer ko simple Hindi/Hinglish mein exactly yeh 3 cheezein batao:

    1. Fasal kyun sahi hai (1-2 lines — is mitti ke liye {crop} kyun best hai)

    2. Khaad Recommendation (Fertilizer):
       - Konsa khaad daalein (Urea/DAP/NPK etc.)
       - Kitni maatra mein (per acre)
       - Kab daalein (bawaai ke pehle ya baad)

    3. Sinchai Schedule (Irrigation):
       - Kitne din baad paani dein
       - Kitna paani chahiye
       - Kaunsa time best hai (subah/shaam)

    Short aur clear rakho. Max 150 words total.
    """
    
    # Step 3: Get Groq response
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "Tu ek expert Indian Kisan Sevak hai. Hamesha Hindi/Hinglish mein jawab de. Simple aur clear bhasha use kar."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300
    )
    
    # Step 4: Extract advice
    advice = response.choices[0].message.content
    
    return {
        "recommended_crop": crop,
        "agent_advice": advice
    }


# Test
if __name__ == "__main__":
    print("Testing Soil Sense Agent...\n")
    
    result = soil_sense_agent(90, 42, 43, 20.8, 82.0, 6.5, 202.9)
    
    print("=" * 50)
    print(f"Recommended Crop: {result['recommended_crop'].upper()}")
    print("=" * 50)
    print(f"\nAgent Advice:\n{result['agent_advice']}")
    print("=" * 50)