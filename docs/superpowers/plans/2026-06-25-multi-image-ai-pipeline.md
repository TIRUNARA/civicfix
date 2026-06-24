# Multi-Image Upload & AI Decoupled pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-image upload capabilities and integrate an advanced decoupled AI pipeline that aggregates multiple visual descriptions plus optional user notes to classify hazard metadata.

**Architecture:** 
1. **Database Schema Compatibility**: Store multiple image paths as a JSON array serialized in the existing `image_path` TEXT column (e.g., `["/uploads/img_0.jpg", "/uploads/img_1.jpg"]`). If a single image path is stored as a plain string, fallback cleanly to a single-element list.
2. **AI Pipeline Extent**: Loop Stage 1 (Vision description) over all uploaded images, producing a detailed physical visual description for each image. Pass all descriptions along with the user's optional note to Stage 2 (Text classification) to yield the final structured tags, department, priority, and unified human summary.
3. **Frontend Presentation**: Render a sleek, interactive multi-image carousel/grid in the dashboard and map details modals with smooth transition states.

**Tech Stack:** Python 3, google-generativeai, FastAPI, HTML, Javascript, Tailwind CSS.

---

### Task 1: Update `gemini_service.py` to Support Multi-Image AI Decoupled Processing

**Files:**
- Modify: `gemini_service.py`

- [ ] **Step 1: Replace/extend `analyze_report_image` with a multi-image `analyze_report_images` function**

Update `gemini_service.py` to process multiple images and optional user text note:

```python
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
            "analysis": f"Multi-image analysis (mock). Processed {len(images_bytes)} images. Note: {user_note or 'None'}"
        }
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # --- Stage 1: Vision-Only Physical Description for each image ---
        descriptions = []
        vision_prompt = """
        You are an expert civic infrastructure inspector.
        Analyze this image of a municipal hazard.
        Provide a highly concise, precise, and objective visual description of the hazard.
        Focus on describing:
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
```

- [ ] **Step 2: Update `analyze_report_image` to map to `analyze_report_images` for compatibility**

```python
def analyze_report_image(image_bytes: bytes) -> dict:
    return analyze_report_images([image_bytes])
```

---

### Task 2: Update FastAPI Endpoints in `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update `/api/sessions/upload/{token}` to handle multiple images and `user_note`**

```python
@app.post("/api/sessions/upload/{token}")
async def upload_session_photo(
    token: str,
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None), # Backward compatibility fallback
    latitude: float = Form(...),
    longitude: float = Form(...),
    user_note: str = Form(None)
):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Gather uploaded files
    uploaded_files = []
    if images:
        uploaded_files = images
    elif image:
        uploaded_files = [image]
        
    if not uploaded_files:
        conn.close()
        raise HTTPException(status_code=400, detail="No images uploaded")
        
    saved_paths = []
    images_bytes = []
    
    # Save each file and collect bytes
    for idx, file in enumerate(uploaded_files):
        contents = await file.read()
        images_bytes.append(contents)
        
        filename = f"draft_{token}_{idx}.jpg"
        filepath = os.path.join("/tmp/uploads", filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        saved_paths.append(f"/uploads/{filename}")
        
    # Run multi-image decoupled analysis
    ai_data = gemini_service.analyze_report_images(images_bytes, user_note)
    
    draft_data = {
        "image_path": json.dumps(saved_paths), # Serialized list of paths
        "latitude": latitude,
        "longitude": longitude,
        "tags": ai_data["tags"],
        "department": ai_data["department"],
        "priority": ai_data["priority"],
        "analysis": ai_data["analysis"],
        "user_note": user_note
    }
    
    cursor.execute(
        "UPDATE qr_sessions SET status = 'draft', draft_data = ? WHERE token = ?",
        (json.dumps(draft_data), token)
    )
    conn.commit()
    conn.close()
    
    return {"status": "draft", "draft_data": draft_data}
```

- [ ] **Step 2: Update `/api/reports/submit` to handle multiple images or image paths**

Ensure `/api/reports/submit` preserves JSON-serialized multiple image paths if provided.

```python
@app.post("/api/reports/submit")
async def submit_report(
    image: List[UploadFile] = File(None), # Allow list of images direct upload
    image_path: str = Form(None),         # JSON array string or plain path string
    latitude: float = Form(...),
    longitude: float = Form(...),
    tags: str = Form(...), 
    department: str = Form(...),
    priority: int = Form(...),
    description: str = Form(...),
    reporter_email: str = Form("anonymous@civicfix.org"),
    reporter_name: str = Form("Anonymous"),
    reporter_avatar: str = Form(""),
    token: str = Form(None)
):
    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    final_db_paths = []
    
    if image:
        for idx, img_file in enumerate(image):
            filename = f"{report_id}_before_{idx}.jpg"
            filepath = os.path.join("/tmp/uploads", filename)
            contents = await img_file.read()
            with open(filepath, "wb") as f:
                f.write(contents)
            final_db_paths.append(f"/uploads/{filename}")
            
    elif image_path:
        # Check if it is a JSON list of paths
        try:
            paths = json.loads(image_path)
            if not isinstance(paths, list):
                paths = [image_path]
        except Exception:
            paths = [image_path]
            
        for idx, path in enumerate(paths):
            local_path = path
            if path.startswith("/uploads/"):
                local_path = path.replace("/uploads/", "/tmp/uploads/", 1)
            if not os.path.abspath(local_path).startswith("/tmp/uploads/"):
                raise HTTPException(status_code=400, detail="Invalid image path")
            if not os.path.exists(local_path):
                raise HTTPException(status_code=404, detail=f"Draft image not found: {path}")
                
            # Copy to report persistent files
            filename = f"{report_id}_before_{idx}.jpg"
            filepath = os.path.join("/tmp/uploads", filename)
            with open(local_path, "rb") as src, open(filepath, "wb") as dst:
                dst.write(src.read())
            final_db_paths.append(f"/uploads/{filename}")
    else:
        raise HTTPException(status_code=400, detail="No images provided")
        
    try:
        tags_list = json.loads(tags)
    except Exception:
        tags_list = [tags]
        
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Calculate proximity priority bonus
    cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved'")
    active_reports = cursor.fetchall()
    
    priority_bonus = 0
    for rep in active_reports:
        dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
        if dist <= 0.075:
            priority_bonus += 1
            cursor.execute("UPDATE reports SET votes = votes + 1 WHERE id = ?", (rep["id"],))
            
    final_priority = min(5, priority + priority_bonus)
    now_str = datetime.utcnow().isoformat()
    
    # Store list of paths as JSON serialized string
    db_image_path_str = json.dumps(final_db_paths)
    
    cursor.execute("""
    INSERT INTO reports (
        id, latitude, longitude, image_path, tags, department, priority, 
        votes, status, created_at, updated_at, reporter_email, reporter_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, latitude, longitude, db_image_path_str, json.dumps(tags_list), 
        department, final_priority, 1, "Reported", now_str, now_str, 
        reporter_email, reporter_name
    ))
    
    # Leaderboard updates
    cursor.execute("SELECT civic_points, reports_submitted FROM leaderboard WHERE email = ?", (reporter_email,))
    lead_row = cursor.fetchone()
    if lead_row:
        new_pts = lead_row["civic_points"] + 10
        new_subs = lead_row["reports_submitted"] + 1
        cursor.execute("UPDATE leaderboard SET civic_points = ?, reports_submitted = ?, username = ?, avatar_url = ? WHERE email = ?", (
            new_pts, new_subs, reporter_name, reporter_avatar, reporter_email
        ))
    else:
        cursor.execute("""
        INSERT INTO leaderboard (email, username, avatar_url, civic_points, reports_submitted)
        VALUES (?, ?, ?, 10, 1)
        """, (reporter_email, reporter_name, reporter_avatar))
        
    if token:
        cursor.execute("UPDATE qr_sessions SET status = 'uploaded', associated_report_id = ? WHERE token = ?", (report_id, token))
        
    conn.commit()
    conn.close()
    
    return {"id": report_id, "status": "Reported", "priority": final_priority}
```

---

### Task 3: Update Frontend Templates to Render Image Carousels / Lists

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `templates/map.html`

- [ ] **Step 1: Refactor image parsing helper in `templates/dashboard.html`**

Define a JavaScript utility to clean and parse the image paths, and integrate carousel slider markup/logic in the detail modal:

Modify `templates/dashboard.html` openDetailModal function to support displaying multiple images dynamically.

```javascript
// Render Image Carousel helper
function renderImageCarousel(elementId, pathString, fallbackAlt) {
    const container = document.getElementById(elementId);
    let paths = [];
    try {
        paths = JSON.parse(pathString);
        if (!Array.isArray(paths)) {
            paths = [pathString];
        }
    } catch(e) {
        paths = [pathString];
    }
    
    // Clear and build carousel HTML
    container.innerHTML = "";
    if (paths.length === 0) {
        container.innerHTML = `<div class="w-full h-48 bg-slate-900 flex items-center justify-center text-slate-500">No Image</div>`;
        return;
    }
    
    // Create image element and navigation controls
    const wrapper = document.createElement("div");
    wrapper.className = "relative w-full h-48 rounded-2xl overflow-hidden border border-white/10 bg-slate-950";
    
    const imgEl = document.createElement("img");
    imgEl.className = "w-full h-full object-cover transition-opacity duration-300";
    imgEl.src = paths[0];
    imgEl.alt = fallbackAlt;
    wrapper.appendChild(imgEl);
    
    if (paths.length > 1) {
        let activeIdx = 0;
        
        const prevBtn = document.createElement("button");
        prevBtn.className = "absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-slate-950/70 border border-white/10 flex items-center justify-center text-white hover:bg-slate-950 font-bold z-10 text-xs";
        prevBtn.innerHTML = "❮";
        prevBtn.onclick = (e) => {
            e.stopPropagation();
            activeIdx = (activeIdx - 1 + paths.length) % paths.length;
            imgEl.style.opacity = 0;
            setTimeout(() => {
                imgEl.src = paths[activeIdx];
                imgEl.style.opacity = 1;
            }, 150);
        };
        
        const nextBtn = document.createElement("button");
        nextBtn.className = "absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-slate-950/70 border border-white/10 flex items-center justify-center text-white hover:bg-slate-950 font-bold z-10 text-xs";
        nextBtn.innerHTML = "❯";
        nextBtn.onclick = (e) => {
            e.stopPropagation();
            activeIdx = (activeIdx + 1) % paths.length;
            imgEl.style.opacity = 0;
            setTimeout(() => {
                imgEl.src = paths[activeIdx];
                imgEl.style.opacity = 1;
            }, 150);
        };
        
        const indicator = document.createElement("span");
        indicator.className = "absolute bottom-2 right-2 px-2 py-0.5 rounded-lg bg-slate-950/80 text-[10px] text-slate-300 font-mono";
        indicator.textContent = `1/${paths.length}`;
        
        prevBtn.addEventListener("click", () => {
            indicator.textContent = `${activeIdx + 1}/${paths.length}`;
        });
        nextBtn.addEventListener("click", () => {
            indicator.textContent = `${activeIdx + 1}/${paths.length}`;
        });
        
        wrapper.appendChild(prevBtn);
        wrapper.appendChild(nextBtn);
        wrapper.appendChild(indicator);
    }
    
    container.appendChild(wrapper);
}
```

Replace the single image rendering block in `openDetailModal` with:
```javascript
            // Old image tag replacement
            const beforeCol = document.getElementById("modalBeforeImage").parentNode;
            beforeCol.id = "carouselBeforeContainer";
            beforeCol.innerHTML = `<span class="text-2xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Original Hazard Image</span>
                                   <div id="beforeCarousel"></div>`;
            renderImageCarousel("beforeCarousel", r.image_path, "Before");
```

- [ ] **Step 2: Mirror the image carousel helper in `templates/map.html`**

Update `templates/map.html` marker creation popup and hover cards to cleanly fetch/extract the first image if `image_path` contains multiple values:
```javascript
// Get first image from path
function getFirstImagePath(pathString) {
    try {
        const paths = JSON.parse(pathString);
        return Array.isArray(paths) ? paths[0] : pathString;
    } catch(e) {
        return pathString;
    }
}
```
Apply this helper when rendering Leaflet hover cards and map click popups.

---

### Task 4: Validate Implementation & Integration

- [ ] **Step 1: Write integration tests in `test_multistage_flow.py` for multiple image upload**
- [ ] **Step 2: Run verification scripts using the virtual environment python interpreter**
