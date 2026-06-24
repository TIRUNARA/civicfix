import os
import json
import google.generativeai as genai
from PIL import Image
import io

API_KEY = os.environ.get("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def analyze_report_images(images_bytes: list, user_note: str = None) -> dict:
    """
    Processes multiple images through Stage 1 (Vision details extraction),
    then aggregates all descriptions and user_note through Stage 2 (Text classification JSON).
    """
    if not API_KEY:
        return {
            "tags": ["Pothole", "Broken Asphalt"],
            "department": "Roads & Traffic",
            "priority": 4,
            "analysis": f"A deep pothole (approximately 1 meter wide) blocking traffic on the secondary lane. User note: {user_note or 'None'}"
        }
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # --- Stage 1: Vision-Only Physical Description for each image ---
        descriptions = []
        vision_prompt = """
        You are an expert civic infrastructure inspector.
        Analyze this image of a municipal hazard.
        Provide a highly concise, precise, and objective visual description of the hazard.
        Do NOT categorize or format as JSON yet.
        Instead, focus on describing:
        1. The exact type of hazard (e.g. pothole, broken streetlight, fallen tree, overflow trash, water leakage).
        2. The material and context (e.g. asphalt, concrete road, overhead wires, metal pole).
        3. The physical scale, dimensions, or size of the problem (e.g. 'approx. 1 meter wide pothole', 'tree branches leaning on a power line').
        4. The immediate severity and danger clues.
        Your description should be extremely concise (2-3 sentences max) and contain only factual visual observations.
        """
        
        for idx, img_bytes in enumerate(images_bytes):
            image = Image.open(io.BytesIO(img_bytes))
            response = model.generate_content([vision_prompt, image])
            desc = response.text.strip()
            descriptions.append(f"Image {idx + 1} Visual Description: {desc}")
            
        aggregated_descriptions = "\n\n".join(descriptions)
        
        # --- Stage 2: Text-Only Classification and Structuring ---
        text_prompt = f"""
        You are a municipal dispatch assistant.
        Analyze the following visual description(s) of a civic hazard, and incorporate the reporter's personal note if provided.
        
        Visual Description(s):
        {aggregated_descriptions}
        
        Reporter's Note:
        "{user_note or 'No note provided'}"
        
        You MUST return a valid JSON object matching this structure:
        {{
          "tags": ["tag1", "tag2"],
          "department": "Roads & Traffic" | "Water & Sanitation" | "Electrical" | "Waste Management" | "Forestry & Parks" | "Other",
          "priority": 1-5,
          "analysis": "A clear, polished, and human-friendly description of the issue for the reporting dashboard (1-2 sentences)."
        }}
        
        Guidelines for classification:
        - "tags": Generates 2-4 concise tags identifying the hazard type and physical context (e.g. ["Pothole", "Broken Asphalt"]).
        - "department": Assigns to the most appropriate category based on the visual description:
          * "Roads & Traffic" (potholes, damaged asphalt, traffic signs, sidewalk blocks)
          * "Water & Sanitation" (water leaks, open drains, pipe bursts, sewer issues)
          * "Electrical" (exposed wires, broken streetlights, leaning poles, power line blockages)
          * "Waste Management" (garbage overflow, illegal dumping, littering)
          * "Forestry & Parks" (fallen trees, overgrown brush, broken branches, park damage)
          * "Other" (for anything else)
        - "priority": Map the priority score from 1 (lowest, minor inconvenience) to 5 (critical emergency/severe hazard) based on the threat level described:
          * 5: Critical danger/risk to life (exposed high-voltage wires, deep open manholes, tree leaning on power lines, complete road blockage).
          * 4: Major safety hazard (pothole on high-speed road, large tree blocking one lane, broken streetlight at a dark intersection).
          * 3: Moderate hazard (pothole on secondary road, minor garbage overflow, non-critical water leak).
          * 2: Minor hazard/inconvenience (small pothole in a parking lot, minor graffiti).
          * 1: Aesthetic/low impact issues.
        """
        
        text_response = model.generate_content([text_prompt])
        text_output = text_response.text.strip().replace("```json", "").replace("```", "").strip()
        
        return json.loads(text_output)
        
    except Exception as e:
        return {
            "tags": ["unknown"],
            "department": "Other",
            "priority": 1,
            "analysis": f"Failed to process multi-image two-stage AI diagnostics: {str(e)}"
        }

def analyze_report_image(image_bytes: bytes) -> dict:
    return analyze_report_images([image_bytes])

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
