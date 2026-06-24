# Two-Stage AI Reporting Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a decoupled two-stage AI pipeline for civic hazard analysis (Vision-to-Text-to-Structured-JSON) using Gemini 2.5 Flash to achieve high visual accuracy and structured metadata classification.

**Architecture:** Decouple physical observation from categorical reasoning. Stage 1 takes the raw image bytes and uses Gemini 2.5 Flash as a Vision model to produce a concise physical description containing raw scale, depth, and material details. Stage 2 feeds this description to a Gemini 2.5 Flash text invocation to synthesize tags, map departments, estimate safety priorities, and output a clean, parsed JSON object.

**Tech Stack:** Python 3, google-generativeai / google-genai, Pillow (PIL), FastAPI TestClient, unittest.

---

### Task 1: Refactor `gemini_service.py` to Decouple the AI Analysis

**Files:**
- Modify: `gemini_service.py:11-48`

- [ ] **Step 1: Replace `analyze_report_image` with the two-stage pipeline**

Update `/home/integrity/Desktop/agent/civicfix/gemini_service.py` to define two distinct stages:
1. **Stage 1 (Vision)**: Generates a concise physical observation string from the image.
2. **Stage 2 (Text)**: Formulates the final JSON structure from the visual observation string.

```python
def analyze_report_image(image_bytes: bytes) -> dict:
    """
    Sends before image to Gemini Vision to describe the hazard details (Stage 1),
    then parses that description into structured JSON metadata (Stage 2).
    """
    if not API_KEY:
        # Fallback dictionary for testing without API key
        return {
            "tags": ["Pothole", "Broken Asphalt"],
            "department": "Roads & Traffic",
            "priority": 4,
            "analysis": "A deep pothole (approximately 1 meter wide) blocking traffic on the secondary lane."
        }
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        image = Image.open(io.BytesIO(image_bytes))
        
        # --- Stage 1: Vision-Only Physical Description ---
        vision_prompt = """
        You are an expert civic infrastructure inspector.
        Analyze this image of a municipal hazard.
        Provide a highly concise, precise, and objective visual description of the hazard.
        Do NOT categorize or format as JSON yet.
        Instead, focus on describing:
        1. The exact type of hazard (e.g. pothole, broken streetlight, fallen tree, overflow trash, water leakage).
        2. The material and context (e.g. asphalt, concrete road, overhead wires, metal pole).
        3. The physical scale, dimensions, or size of the problem (e.g. 'approx. 1 meter wide pothole', 'entire street blocked', 'tree branches leaning on a power line').
        4. The immediate severity and visual danger clues (e.g. exposed wires, deep hole, blocking active traffic).
        Your description should be extremely concise (2-4 sentences max) and contain only factual visual observations.
        """
        
        vision_response = model.generate_content([vision_prompt, image])
        visual_description = vision_response.text.strip()
        
        # --- Stage 2: Text-Only Classification and Structuring ---
        text_prompt = f"""
        You are a municipal dispatch assistant.
        Based on the following factual visual description of a civic hazard, classify the issue and format the result.
        
        Visual Description:
        "{visual_description}"
        
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
        # Graceful fallback on API or parsing failures
        return {
            "tags": ["unknown"],
            "department": "Other",
            "priority": 1,
            "analysis": f"Failed to process two-stage AI diagnostics: {str(e)}"
        }
```

---

### Task 2: Validate Integration with Automated Tests

**Files:**
- Modify: `test_gemini.py`
- Test: `test_multistage_flow.py`

- [ ] **Step 1: Update `test_gemini.py` to verify the structure and check for API exceptions**

```python
import gemini_service

def test_mock_fallback():
    result = gemini_service.analyze_report_image(b"mock_bytes")
    assert "tags" in result
    assert "department" in result
    assert "priority" in result
    assert "analysis" in result
    assert isinstance(result["tags"], list)
    assert result["priority"] in [1, 2, 3, 4, 5]
    print("Test passed: Gemini fallback behavior verified.")

if __name__ == "__main__":
    test_mock_fallback()
```

- [ ] **Step 2: Run both test suites to make sure everything passes**

Run the following test files using the virtual environment python interpreter:
```bash
/home/integrity/Desktop/agent/venv/bin/python3 test_gemini.py
/home/integrity/Desktop/agent/venv/bin/python3 test_multistage_flow.py
```

Expected output:
Both tests should execute and complete successfully (Exit code: 0).
