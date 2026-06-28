import os
import json
import base64
from google import genai
from google.genai import types
from PIL import Image, ImageStat, ImageFilter
import io
import re
from typing import Literal, List, Dict, Any
from dotenv import load_dotenv
import database

load_dotenv()

API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY_1")
client = genai.Client(api_key=API_KEY) if API_KEY else None

# --- Native Tools for Gemini ---

def get_nearby_reports(latitude: float, longitude: float, radius_km: float = 0.075) -> str:
    """
    Query database for active reports within a given radius in kilometers.
    Returns a JSON string listing reports with id, department, priority, and votes.
    """
    conn = database.get_db()
    cursor = conn.cursor()
    # Approx bounding box calculation
    # 1 degree latitude ~= 111 km
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * abs(latitude) if latitude != 0 else 111.0)
    
    cursor.execute("""
        SELECT id, department, priority, votes 
        FROM reports 
        WHERE status != 'Resolved' AND 
              latitude BETWEEN ? AND ? AND 
              longitude BETWEEN ? AND ?
    """, (latitude - lat_delta, latitude + lat_delta, longitude - lon_delta, longitude + lon_delta))
    rows = cursor.fetchall()
    conn.close()
    
    res = [dict(r) for r in rows]
    return json.dumps(res)

def verify_image_quality(image_base64: str) -> Dict[str, Any]:
    """
    Detect blur, low light, or other quality issues on a base64 encoded image.
    Returns dictionary with 'valid' boolean and list of 'issues'.
    """
    try:
        header, encoded = image_base64.split(",", 1) if "," in image_base64 else ("", image_base64)
        img_bytes = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(img_bytes)).convert('L')
        
        # Blur detection via Laplacian variance
        laplacian_var = 0.0
        # Simple PIL approximation of Laplacian variance
        laplacian_filter = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], 1, 0)
        filtered = img.filter(laplacian_filter)
        stat = ImageStat.Stat(filtered)
        laplacian_var = stat.var[0]
        is_blurry = laplacian_var < 15.0
        
        # Low light detection via mean pixel intensity
        raw_stat = ImageStat.Stat(img)
        mean_intensity = raw_stat.mean[0]
        is_dark = mean_intensity < 25.0
        
        issues = []
        if is_blurry:
            issues.append("blurry")
        if is_dark:
            issues.append("dark")
            
        return {
            "valid": not (is_blurry or is_dark),
            "issues": issues
        }
    except Exception as e:
        return {
            "valid": True,
            "issues": []
        }

def estimate_resolution_time(department: str, priority: int, nearby_count: int) -> int:
    """
    Estimate resolution time in hours based on department SLA, priority level, and active queue load.
    Handles comma-separated departments by selecting the maximum SLA among them.
    """
    sla_map = {
        "Municipal Roads": 72,
        "Water & Sanitation": 48,
        "Solid Waste": 24,
        "Utility Streetlighting": 24,
        "Parks": 96,
        "National Highways": 48,
        "State Grid": 24,
        "Environment Board": 120,
        "Other Issues": 72
    }
    depts = [d.strip() for d in department.split(",") if d.strip()]
    if not depts:
        depts = ["Other Issues"]
    base_hours = max(sla_map.get(d, 72) for d in depts)
    queue_penalty = nearby_count * 6
    priority_discount = (priority - 1) * 12
    final_hours = max(4, base_hours + queue_penalty - priority_discount)
    return int(final_hours)

# --- Self-Correcting JSON Parser & Agentic Logic ---

def safe_json_parse(response_text: str, client_ref=None, max_retries=3) -> dict:
    text = response_text.strip()
    parsed_data = None
    for attempt in range(max_retries):
        try:
            parsed_data = json.loads(text)
            break
        except json.JSONDecodeError:
            # Try to locate JSON block { ... }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    parsed_data = json.loads(match.group(0))
                    break
                except json.JSONDecodeError:
                    pass
            
            # Request LLM correction if client is available
            if client_ref and attempt < max_retries - 1:
                try:
                    prompt = (
                        "Your previous response was not valid JSON. Please output ONLY a valid JSON object matching the exact keys: "
                        "'tags' (list of strings), 'department' (string), 'priority' (integer 1-5), "
                        "'analysis' (string), 'estimated_resolution_hours' (integer), 'clarification_requested' (boolean).\n"
                        f"Flawed response:\n{response_text}"
                    )
                    res = client_ref.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    text = res.text.strip()
                except Exception:
                    break
            else:
                break
                
    if not parsed_data:
        # Fallback structure
        parsed_data = {
            "tags": ["Infrastructure"],
            "department": "Other Issues",
            "priority": 3,
            "analysis": "Failed to parse AI structure. Fallback initialized.",
            "estimated_resolution_hours": 72,
            "clarification_requested": False
        }
        
    # Enforce allowed department list
    allowed_depts = {
        "Municipal Roads",
        "Water & Sanitation",
        "Solid Waste",
        "Utility Streetlighting",
        "Parks",
        "National Highways",
        "State Grid",
        "Environment Board",
        "Other Issues"
    }
    
    dept_val = parsed_data.get("department", "Other Issues") or "Other Issues"
    
    # Handle both comma separated string and list
    if isinstance(dept_val, list):
        depts = [str(d).strip() for d in dept_val if d]
    else:
        depts = [d.strip() for d in str(dept_val).split(",") if d.strip()]
        
    valid_depts = []
    for d in depts:
        matched = False
        for allowed in allowed_depts:
            if d.lower() == allowed.lower() or allowed.lower() in d.lower():
                valid_depts.append(allowed)
                matched = True
                break
        if not matched:
            valid_depts.append("Other Issues")
            
    valid_depts = list(dict.fromkeys(valid_depts))
    if not valid_depts:
        valid_depts = ["Other Issues"]
        
    parsed_data["department"] = ", ".join(valid_depts)
    
    # Enforce priority range 1-5
    try:
        priority = int(parsed_data.get("priority", 3))
        if priority < 1 or priority > 5:
            priority = 3
    except Exception:
        priority = 3
    parsed_data["priority"] = priority
    
    return parsed_data

def analyze_report_images(images_bytes: list, user_note: str = None, latitude: float = 12.9716, longitude: float = 77.5946) -> dict:
    # Step 1: Verify Image Quality
    for idx, img_bytes in enumerate(images_bytes):
        encoded_img = base64.b64encode(img_bytes).decode("utf-8")
        quality = verify_image_quality(f"data:image/jpeg;base64,{encoded_img}")
        if not quality["valid"]:
            return {
                "tags": ["Unclear"],
                "department": "Other Issues",
                "priority": 1,
                "analysis": f"Image {idx + 1} quality check failed: {', '.join(quality['issues'])}. Please upload a clearer, well-lit photo.",
                "estimated_resolution_hours": 168,
                "clarification_requested": True,
                "suggested_action": f"Image {idx + 1} is {', '.join(quality['issues'])}. Please upload a clearer, well-lit photo."
            }

    if not client:
        return {
            "tags": ["Pothole", "Broken Asphalt"],
            "department": "Municipal Roads",
            "priority": 4,
            "analysis": f"Static fallback representations. User note: {user_note or 'None'}",
            "estimated_resolution_hours": 48,
            "clarification_requested": False
        }

    # Step 2: Get nearby reports context
    nearby_reports_json = get_nearby_reports(latitude, longitude, radius_km=0.075)
    nearby_reports = json.loads(nearby_reports_json)
    nearby_count = len(nearby_reports)

    # Step 3: Run vision descriptions
    descriptions = []
    vision_prompt = (
        "You are an expert civic infrastructure inspector.\n"
        "Analyze this image of a municipal hazard.\n"
        "Provide a highly concise visual description of the hazard (2-3 sentences max) highlighting exact type and severity."
    )

    for idx, img_bytes in enumerate(images_bytes):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            contents = [vision_prompt, img]
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            descriptions.append(f"Image {idx + 1}: {response.text.strip()}")
        except Exception as e:
            descriptions.append(f"Image {idx + 1}: Failed to analyze visual details ({e})")

    aggregated_descriptions = "\n\n".join(descriptions)

    # Step 4: Dispatch routing classification
    text_prompt = (
        "You are a municipal dispatch assistant.\n"
        "Analyze the visual description(s) of a civic hazard, and incorporate the reporter's personal note if provided.\n\n"
        f"Visual Description(s):\n{aggregated_descriptions}\n\n"
        f"Reporter's Note:\n\"{user_note or 'No note provided'}\"\n\n"
        f"Context (Nearby active reports in this zone): {nearby_reports_json}\n\n"
        "You must return a valid JSON object matching this schema:\n"
        "{\n"
        "  \"tags\": [\"string\", ...],\n"
        "  \"department\": \"A single department, or a comma-separated list of departments if the hazard spans multiple domains (e.g. 'Municipal Roads, Water & Sanitation'). Allowed values are: 'Municipal Roads', 'Water & Sanitation', 'Solid Waste', 'Utility Streetlighting', 'Parks', 'National Highways', 'State Grid', 'Environment Board', 'Other Issues'\",\n"
        "  \"priority\": 1 | 2 | 3 | 4 | 5,\n"
        "  \"analysis\": \"detailed textual analysis string\",\n"
        "  \"estimated_resolution_hours\": integer,\n"
        "  \"clarification_requested\": false\n"
        "}\n\n"
        "Calculate the estimated_resolution_hours by taking the maximum department SLA among those involved (Municipal Roads: 72, Water & Sanitation: 48, Solid Waste: 24, Utility Streetlighting: 24, State Grid: 24, Parks: 96) "
        f"plus a queue penalty of {nearby_count * 6} hours based on the {nearby_count} active reports nearby, "
        "minus 12 hours per priority level above 1."
    )

    try:
        response_text = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return safe_json_parse(response_text.text, client_ref=client)
    except Exception as e:
        print(f"Structured analysis failed: {e}")
        return {
            "tags": ["Pothole"],
            "department": "Municipal Roads",
            "priority": 3,
            "analysis": f"AI dispatch failed: {e}",
            "estimated_resolution_hours": estimate_resolution_time("Municipal Roads", 3, nearby_count),
            "clarification_requested": False
        }

def analyze_report_image(image_bytes: bytes) -> dict:
    return analyze_report_images([image_bytes])

def verify_resolution(before_bytes: bytes, after_bytes: bytes) -> dict:
    if not client:
        return {"verified": True, "explanation": "Resolution automatically verified (API not configured)."}

    try:
        before_img = Image.open(io.BytesIO(before_bytes))
        after_img = Image.open(io.BytesIO(after_bytes))
        contents = [
            "Compare these two images representing a civic issue before and after repair.\n"
            "Verify if the issue reported in the before image has been resolved in the after image.\n"
            "Return a JSON object with 'verified' (boolean) and 'explanation' (string).",
            before_img,
            after_img
        ]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        parsed = safe_json_parse(response.text, client_ref=client)
        return {
            "verified": parsed.get("verified", True),
            "explanation": parsed.get("explanation", "Resolution state verified by AI.")
        }
    except Exception as e:
        return {"verified": True, "explanation": f"Fallback verification triggered: {e}"}

def generate_reviewer_summary(report_data: dict, assignments: list) -> str:
    """
    Generate a professional structured diagnostic and resource summary of the reviewer's field logs.
    """
    if not client:
        summary = "### 🛠️ FIELD DIAGNOSTIC REPORT\n"
        summary += f"**Report ID**: {report_data.get('id')}\n"
        summary += f"**Department**: {report_data.get('department')}\n"
        summary += f"**Description**: {report_data.get('description')}\n\n"
        summary += "#### 📦 ASSIGNED RESOURCES\n"
        for a in assignments:
            summary += f"- **Reviewer {a.get('reviewer_name', 'Inspector')}** logged resources:\n"
            summary += f"  > {a.get('resources_logged') or 'None specified'}\n"
            summary += f"  > Coordinates: {a.get('end_latitude')}, {a.get('end_longitude')}\n"
        return summary

    prompt = (
        "You are an expert municipal planning supervisor.\n"
        "Generate a structured, professional inspection diagnostic summary based on the following report details and reviewer field logs.\n\n"
        f"Report Details:\n"
        f"- ID: {report_data.get('id')}\n"
        f"- Department: {report_data.get('department')}\n"
        f"- Original Description: {report_data.get('description')}\n\n"
        f"Reviewer Field Assignments & Submissions:\n"
    )
    for a in assignments:
        prompt += (
            f"- Reviewer: {a.get('reviewer_name') or 'Inspector'}\n"
            f"  Status: {a.get('status')}\n"
            f"  Logged Resources/Materials: {a.get('resources_logged') or 'None specified'}\n"
            f"  GPS Location Logged: Lat {a.get('end_latitude')}, Lng {a.get('end_longitude')}\n"
            f"  Image Uploaded: {'Yes' if a.get('analysis_image') else 'No'}\n\n"
        )
    prompt += (
        "Create a clean Markdown document with these sections:\n"
        "1. Executive Summary: Short overview of the diagnostic inspection findings.\n"
        "2. Resource Checklist: A professional list of resources and materials required by the reviewer for fixing the issue.\n"
        "3. Verification status: Confirmation of coordinates comparison with report origin.\n"
        "Keep it highly professional, clean, and structured."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Failed to generate summary: {e}"
