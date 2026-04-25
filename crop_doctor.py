import os
import base64
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

def encode_image(image_path):
    """Convert image file to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def crop_doctor_agent(image_path, crop_name=None):
    """
    Diagnose crop disease from image and suggest treatment
    image_path: path to the uploaded image file
    crop_name: optional — farmer can mention which crop it is
    """
    
    # Encode image to base64
    base64_image = encode_image(image_path)
    
    # Build prompt
    crop_info = f"Fasal ka naam: {crop_name}" if crop_name else "Fasal ka naam farmer ne nahi bataya"
    
    prompt = f"""
    Tu ek expert Indian Krishi Doctor (Crop Disease Specialist) hai.
    
    {crop_info}
    
    Farmer ne apni bimaar fasal ki photo bheji hai. Photo dekh kar batao:

    1. Bimari ka Naam (Disease Name):
       - Kya bimari hai (Hindi + English name)
    
    2. Bimari ki Pehchaan (Symptoms):
       - Photo mein kya dikh raha hai
       - Yeh bimari kyun hoti hai
    
    3. Ilaaj (Treatment):
       - Konsa spray/dawa use karein (specific name)
       - Kitni maatra mein
       - Kab aur kaise lagayein
    
    4. Bachao (Prevention):
       - Aage se yeh bimari kaise rokein
       - 2-3 simple tips
    
    Simple Hindi/Hinglish mein batao. Max 200 words.
    Agar photo mein koi bimari nahi dikh rahi, toh farmer ko batao fasal theek lag rahi hai.
    """
    
    # Call Groq vision model
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  # vision model
        messages=[
            {
                "role": "system",
                "content": "Tu ek expert Indian Krishi Doctor hai jo farmers ki fasal ki bimariyan diagnose karta hai aur Hindi/Hinglish mein ilaaj batata hai."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=400
    )
    
    diagnosis = response.choices[0].message.content
    
    return {
        "status": "success",
        "crop": crop_name if crop_name else "Unknown",
        "diagnosis": diagnosis
    }


# Test
if __name__ == "__main__":
    import sys
    
    print("🌿 KisanMind — Crop Doctor Agent\n")
    
    # Get image path from user
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("Image ka path do (e.g. C:/Users/divya/test.jpg): ")
    
    crop = input("Fasal ka naam batao (optional, Enter skip karo): ").strip()
    crop = crop if crop else None
    
    print("\nDiagnosis ho rahi hai...\n")
    
    result = crop_doctor_agent(image_path, crop)
    
    print("=" * 50)
    print(f"Fasal: {result['crop'].upper()}")
    print("=" * 50)
    print(f"\nDiagnosis:\n{result['diagnosis']}")
    print("=" * 50)