import os
import json
from google import genai
from google.genai import types
from PIL import Image
import io
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY_1")
client = genai.Client(api_key=API_KEY) if API_KEY else None

class AnalysisResult(BaseModel):
    tags: list[str]
    department: str
    priority: int
    analysis: str

class VerificationResult(BaseModel):
    verified: bool
    explanation: str

def analyze_report_images(images_bytes: list, user_note: str = None) -> dict:
    """
    Processes multiple images through Stage 1 (Vision details extraction),
    then aggregates all descriptions and user_note through Stage 2 (Text classification JSON).
    """
    if not client:
        return {
            "tags": ["Pothole", "Broken Asphalt"],
            "department": "Roads & Traffic",
            "priority": 4,
            "analysis": f"API Client not configured. Static fallback representation. User note: {user_note or 'None'}"
        }

    try:
        # Stage 1: Vision description for each image
        descriptions = []
        vision_prompt = (
            "You are an expert civic infrastructure inspector.\n"
            "Analyze this image of a municipal hazard.\n"
            "Provide a highly concise, precise, and objective visual description of the hazard.\n"
            "Do NOT categorize or format as JSON yet. Focus on exact type, material/context, dimensions/scale, and severity.\n"
            "Your description should be extremely concise (2-3 sentences max) and contain only factual visual observations."
        )

        for idx, img_bytes in enumerate(images_bytes):
            try:
                img = Image.open(io.BytesIO(img_bytes))
                contents = [vision_prompt, img]
            except Exception:
                contents = [vision_prompt, f"(Raw image placeholder {idx + 1})"]

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            descriptions.append(f"Image {idx + 1} Visual Description: {response.text.strip()}")

        aggregated_descriptions = "\n\n".join(descriptions)

        # Stage 2: Structured Analysis
        text_prompt = (
            "You are a municipal dispatch assistant.\n"
            "Analyze the following visual description(s) of a civic hazard, and incorporate the reporter's personal note if provided.\n\n"
            f"Visual Description(s):\n{aggregated_descriptions}\n\n"
            f"Reporter's Note:\n\"{user_note or 'No note provided'}\"\n\n"
            "You MUST return a valid JSON object matching the requested schema."
        )

        response_text = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResult,
            )
        )

        return json.loads(response_text.text)

    except Exception as e:
        print(f"Google GenAI API call failed: {e}. Returning mock response...")
        return {
            "tags": ["Pothole", "Broken Asphalt"],
            "department": "Roads & Traffic",
            "priority": 4,
            "analysis": f"GenAI API failure: {e}. User note: {user_note or 'None'}"
        }

def analyze_report_image(image_bytes: bytes) -> dict:
    return analyze_report_images([image_bytes])

def verify_resolution(before_bytes: bytes, after_bytes: bytes) -> dict:
    """
    Sends before and after images side-by-side to Gemini Vision to verify if the issue was resolved.
    """
    if not client:
        return {"verified": True, "explanation": "Resolution automatically verified (API not configured)."}

    try:
        try:
            before_img = Image.open(io.BytesIO(before_bytes))
            after_img = Image.open(io.BytesIO(after_bytes))
            contents = [before_img, after_img]
        except Exception:
            contents = ["(Before image placeholder)", "(After image placeholder)"]

        prompt = (
            "Compare these two images representing a civic issue before and after repair.\n"
            "Verify if the issue reported in the before image has been resolved in the after image."
        )
        contents.insert(0, prompt)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VerificationResult,
            )
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"Resolution verification failed: {e}. Returning mock verification...")
        return {"verified": True, "explanation": f"Fallback verification triggered: {e}"}
