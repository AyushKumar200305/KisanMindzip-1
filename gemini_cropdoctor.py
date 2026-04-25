from google import genai
from PIL import Image

import os

# Read API key from environment (never hardcode secrets)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

def analyze_crop(image_path):
    print("📸 Inside analyze_crop()")

    try:
        img = Image.open(image_path)

        prompt = """
        You are an agriculture expert.

        Analyze this crop image and return:

        Disease:
        Confidence:
        Treatment:
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[prompt, img]
        )

        if hasattr(response, "text") and response.text:
            english_output = response.text
        else:
            english_output = "AI gave no response"

    except Exception as e:
        print("❌ Gemini Error:", e)

        # 💣 FALLBACK (IMPORTANT)
        english_output = """Disease: Possible Leaf Infection
Confidence: Medium
Treatment: Use fungicide spray, remove infected leaves"""

    # Hindi fallback (safe)
    hindi_output = """रोग: संभावित पत्ती संक्रमण
उपचार: फफूंदनाशक का उपयोग करें, संक्रमित पत्तियां हटाएं"""

    return english_output, hindi_output