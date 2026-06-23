import os
import json
import google.generativeai as genai
from PIL import Image
import io

API_KEY = os.environ.get("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def analyze_report_image(image_bytes: bytes) -> dict:
    """
    Sends before image to Gemini Vision to categorize tags, department, priority, and brief analysis.
    """
    if not API_KEY:
        # Fallback dictionary for testing without API key
        return {
            "tags": ["pothole", "asphalt"],
            "department": "Public Works",
            "priority": 3,
            "analysis": "Pothole detected on secondary road."
        }
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    image = Image.open(io.BytesIO(image_bytes))
    
    prompt = """
    Analyze this civic infrastructure report image. You MUST return a valid JSON object matching this structure:
    {
      "tags": ["tag1", "tag2"],
      "department": "Public Works" | "Water Sanitation" | "Electrical" | "Waste Management" | "Other",
      "priority": 1-5,
      "analysis": "Brief 1-sentence description of the issue."
    }
    """
    response = model.generate_content([prompt, image])
    try:
        # Clean potential markdown wrapping
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {
            "tags": ["unknown"],
            "department": "Other",
            "priority": 1,
            "analysis": "Failed to parse AI diagnostic details."
        }

def verify_resolution(before_bytes: bytes, after_bytes: bytes) -> dict:
    """
    Sends before and after images side-by-side to Gemini Vision to verify if the issue was resolved.
    """
    if not API_KEY:
        return {"verified": True, "explanation": "Resolution automatically verified (mock fallback)."}
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    before_img = Image.open(io.BytesIO(before_bytes))
    after_img = Image.open(io.BytesIO(after_bytes))
    
    prompt = """
    Compare these two images representing a civic issue before and after repair. 
    Verify if the issue reported in the before image has been resolved in the after image.
    You MUST return a valid JSON object matching this structure:
    {
      "verified": true | false,
      "explanation": "Brief 1-sentence explanation of your decision."
    }
    """
    response = model.generate_content([prompt, before_img, after_img])
    try:
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"verified": False, "explanation": "Failed to process resolution verification."}
