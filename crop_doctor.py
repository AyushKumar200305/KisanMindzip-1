import os
import re
import base64
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY") or "missing")

SUPPORTED_CROPS = {
    "Wheat":   {"hi": "गेहूं",  "en": "Wheat"},
    "Rice":    {"hi": "चावल",  "en": "Rice"},
    "Potato":  {"hi": "आलू",   "en": "Potato"},
    "Tomato":  {"hi": "टमाटर", "en": "Tomato"},
    "Onion":   {"hi": "प्याज", "en": "Onion"},
    "Cotton":  {"hi": "कपास",  "en": "Cotton"},
}

def encode_image(image_path):
    """Convert image file to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def _lang_rule(language):
    if (language or "").lower().startswith("en"):
        return ("\n\nIMPORTANT: Reply ONLY in clear, simple English. "
                "Do NOT use Hindi or Hinglish words.")
    return ("\n\nIMPORTANT: Reply ONLY in Hindi (Devanagari script). "
            "Use simple, village-friendly Hindi.")

def _is_en(language):
    return (language or "").lower().startswith("en")


def _parse_structured(text, language):
    """
    Parse structured LLM response into dict.
    Falls back to raw text if parsing fails.
    """
    is_english = _is_en(language)
    result = {"disease_name": "", "cause": "", "solution": "", "prevention": ""}

    if is_english:
        patterns = {
            "disease_name": r"DISEASE NAME\s*:\s*(.*?)(?=CAUSE\s*:|$)",
            "cause":        r"CAUSE\s*:\s*(.*?)(?=SOLUTION\s*:|$)",
            "solution":     r"SOLUTION\s*:\s*(.*?)(?=PREVENTION\s*:|$)",
            "prevention":   r"PREVENTION\s*:\s*(.*?)$",
        }
    else:
        patterns = {
            "disease_name": r"रोग का नाम\s*:\s*(.*?)(?=कारण\s*:|$)",
            "cause":        r"कारण\s*:\s*(.*?)(?=समाधान\s*:|$)",
            "solution":     r"समाधान\s*:\s*(.*?)(?=बचाव\s*:|$)",
            "prevention":   r"बचाव\s*:\s*(.*?)$",
        }

    parsed_any = False
    for key, pat in patterns.items():
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            result[key] = m.group(1).strip()
            parsed_any = True

    if not parsed_any:
        result["disease_name"] = text.strip()

    return result


def crop_doctor_agent(image_path, crop_name=None, language="hi", structured=False):
    """
    Diagnose crop disease from image and suggest treatment.
    structured=True: returns parsed dict with disease_name/cause/solution/prevention.
    structured=False: returns raw diagnosis string (backward-compatible).
    """
    base64_image = encode_image(image_path)
    is_english = _is_en(language)

    crop_info_line = (
        f"Crop: {crop_name}" if crop_name else "Crop: Not specified by the farmer"
    ) if is_english else (
        f"फसल: {crop_name}" if crop_name else "फसल का नाम किसान ने नहीं बताया"
    )

    if structured:
        if is_english:
            prompt = f"""You are an expert Indian Crop Disease Specialist.

{crop_info_line}

A farmer has uploaded a photo of their diseased crop. Examine the image carefully and reply EXACTLY in this format (keep the labels as-is):

DISEASE NAME: <name of disease in English (include scientific name if known)>
CAUSE: <what causes this disease — fungus, bacteria, pest, deficiency, etc. — 1-2 sentences>
SOLUTION: <specific pesticide/fungicide/treatment with dosage and timing — 2-3 sentences>
PREVENTION: <2-3 simple tips to prevent this disease in future>

If no disease is visible, write "No disease detected — crop appears healthy" under DISEASE NAME and leave the rest blank.
Keep language simple and farmer-friendly. Max 180 words total."""
        else:
            prompt = f"""आप एक विशेषज्ञ भारतीय फसल रोग विशेषज्ञ हैं।

{crop_info_line}

किसान ने अपनी बीमार फसल की तस्वीर भेजी है। तस्वीर ध्यान से देखें और EXACTLY इस format में जवाब दें (labels वैसे ही रखें):

रोग का नाम: <रोग का नाम हिंदी में (अंग्रेज़ी नाम भी लिखें)>
कारण: <रोग क्यों होता है — फफूंद, बैक्टीरिया, कीट, पोषण की कमी आदि — 1-2 वाक्य>
समाधान: <कौन सी दवाई/स्प्रे करें, कितनी मात्रा में, कब — 2-3 वाक्य>
बचाव: <भविष्य में यह रोग न हो, इसके लिए 2-3 सरल उपाय>

अगर कोई रोग नहीं दिखता, तो रोग का नाम में लिखें "कोई रोग नहीं — फसल स्वस्थ दिखती है" और बाकी खाली छोड़ें।
सरल और किसान-अनुकूल भाषा रखें। कुल 180 शब्द से अधिक नहीं।"""

        sys_msg = (
            "You are an expert Indian crop-disease specialist. Reply ONLY in clear, simple English using the exact format requested."
            if is_english else
            "आप एक विशेषज्ञ भारतीय कृषि डॉक्टर हैं। केवल सरल हिंदी (देवनागरी) में जवाब दें, बिल्कुल उसी format में जो मांगा गया है।"
        )
    else:
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
    
    Max 200 words.
    Agar photo mein koi bimari nahi dikh rahi, toh farmer ko batao fasal theek lag rahi hai.
    """ + _lang_rule(language)

        sys_msg = (
            "You are an expert Indian crop-disease specialist. Always reply in clear, simple English."
            if is_english else
            "Tu ek expert Indian Krishi Doctor hai jo farmers ki fasal ki bimariyan diagnose karta hai aur shuddh Hindi (Devanagari) mein ilaaj batata hai."
        )

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": sys_msg},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        max_tokens=450
    )

    raw = response.choices[0].message.content

    if structured:
        parsed = _parse_structured(raw, language)
        return {
            "status": "success",
            "crop": crop_name if crop_name else "Unknown",
            "structured": True,
            "disease_name": parsed["disease_name"],
            "cause":        parsed["cause"],
            "solution":     parsed["solution"],
            "prevention":   parsed["prevention"],
            "diagnosis":    raw,
        }

    return {
        "status": "success",
        "crop": crop_name if crop_name else "Unknown",
        "diagnosis": raw
    }


if __name__ == "__main__":
    import sys
    print("🌿 KisanMind — Crop Doctor Agent\n")
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("Image ka path do: ")
    crop = input("Fasal ka naam batao (optional, Enter skip karo): ").strip()
    crop = crop if crop else None
    print("\nDiagnosis ho rahi hai...\n")
    result = crop_doctor_agent(image_path, crop)
    print("=" * 50)
    print(f"Fasal: {result['crop'].upper()}")
    print("=" * 50)
    print(f"\nDiagnosis:\n{result['diagnosis']}")
    print("=" * 50)
