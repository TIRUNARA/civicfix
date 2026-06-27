from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import database
import gemini_service
import uuid
import math
import os
from datetime import datetime, timezone
import json
from typing import List
import aiofiles
from pathlib import Path
import base64

def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False

app = FastAPI(title="CivicFix Core")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
database.init_db()

# Haversine distance formula (in km)
def get_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def async_process_report_ai(report_id: str, final_db_paths: list, user_note: str, latitude: float, longitude: float):
    images_bytes = []
    for path in final_db_paths:
        if path.startswith("data:image/"):
            try:
                header, encoded = path.split(",", 1)
                images_bytes.append(base64.b64decode(encoded))
            except Exception as e:
                print(f"Failed to decode base64 image in async_process_report_ai: {e}")
        else:
            local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1) if path.startswith("/uploads/") else path
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        images_bytes.append(f.read())
                except Exception as e:
                    print(f"Failed to read image {local_path}: {e}")
                
    try:
        ai_data = gemini_service.analyze_report_images(images_bytes, user_note)
        tags_list = ai_data.get("tags", ["unknown"])
        dept = ai_data.get("department", "Other")
        priority = ai_data.get("priority", 1)
        description = ai_data.get("analysis", "No description provided.")
        
        conn = database.get_db()
        cursor = conn.cursor()
        
        # Proximity bonus logic
        cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved' AND id != ?", (report_id,))
        active_reports = cursor.fetchall()
        
        priority_bonus = 0
        for rep in active_reports:
            dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
            if dist <= 0.075:
                priority_bonus += 1
                cursor.execute("UPDATE reports SET votes = votes + 1 WHERE id = ?", (rep["id"],))
                
        final_priority = min(5, priority + priority_bonus)
        
        cursor.execute("""
            UPDATE reports
            SET tags = ?, department = ?, priority = ?, description = ?, status = 'Pending', updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(tags_list),
            dept,
            final_priority,
            description,
            datetime.now(timezone.utc).isoformat(),
            report_id
        ))
        conn.commit()
        conn.close()
        print(f"Background AI processing succeeded for report {report_id}")
    except Exception as e:
        print(f"Error in background AI analysis for {report_id}: {e}")

@app.post("/api/reports/analyze")
async def analyze_photo(
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None), # Single image fallback
    user_note: str = Form(None)
):
    uploaded_files = []
    if images:
        uploaded_files = images
    elif image:
        uploaded_files = [image]
        
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No images uploaded")
        
    images_bytes = []
    for file in uploaded_files:
        contents = await file.read()
        images_bytes.append(contents)
        
    ai_data = gemini_service.analyze_report_images(images_bytes, user_note)
    return ai_data

@app.post("/api/reports/submit")
async def submit_report(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None), # Single image fallback
    image_path: str = Form(None), # JSON list of paths or single path string
    latitude: float = Form(...),
    longitude: float = Form(...),
    tags: str = Form(None), # JSON serialized tags list or None
    department: str = Form(None),
    priority: int = Form(None),
    description: str = Form(None),
    user_note: str = Form(None), # Reporter note for AI
    reporter_email: str = Form("anonymous@civicfix.org"),
    reporter_name: str = Form("Anonymous"),
    reporter_avatar: str = Form(""),
    token: str = Form(None) # Optional QR session token to link
):
    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    final_db_paths = []
    
    # Gather uploaded files
    uploaded_files = []
    if images:
        uploaded_files = images
    elif image:
        uploaded_files = [image]
        
    if uploaded_files:
        for idx, img_file in enumerate(uploaded_files):
            filename = f"{report_id}_before_{idx}.jpg"
            filepath = os.path.join(UPLOAD_DIR, filename)
            contents = await img_file.read()
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(contents)
            
            # Convert to base64
            encoded = base64.b64encode(contents).decode("utf-8")
            base64_url = f"data:image/jpeg;base64,{encoded}"
            final_db_paths.append(base64_url)
            
    elif image_path:
        # Check if it is a JSON list of paths
        try:
            paths = json.loads(image_path)
            if not isinstance(paths, list):
                paths = [image_path]
        except Exception:
            paths = [image_path]
            
        base_dir = Path(UPLOAD_DIR)
        for idx, path in enumerate(paths):
            if path.startswith("data:image/"):
                final_db_paths.append(path)
            else:
                local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1) if path.startswith("/uploads/") else path
                path_obj = Path(local_path)
                if not is_safe_path(base_dir, path_obj):
                    raise HTTPException(status_code=400, detail="Access denied")
                resolved_path = str(path_obj.resolve())
                    
                if not os.path.exists(resolved_path):
                    raise HTTPException(status_code=404, detail=f"Draft image not found: {path}")
                    
                filename = f"{report_id}_before_{idx}.jpg"
                filepath = os.path.join(UPLOAD_DIR, filename)
                async with aiofiles.open(resolved_path, "rb") as src:
                    src_contents = await src.read()
                async with aiofiles.open(filepath, "wb") as dst:
                    await dst.write(src_contents)
                
                # Convert copy to base64
                encoded = base64.b64encode(src_contents).decode("utf-8")
                base64_url = f"data:image/jpeg;base64,{encoded}"
                final_db_paths.append(base64_url)
    else:
        raise HTTPException(status_code=400, detail="No images provided")
        
    db_image_path_str = json.dumps(final_db_paths)
    now_str = datetime.now(timezone.utc).isoformat()
    
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Check if this is the async path (tags/department/priority/description are missing)
    is_async = tags is None or department is None or priority is None
    
    if is_async:
        # Insert report in "Processing" state
        status = "Processing"
        initial_tags = ["Processing"]
        initial_dept = "Processing"
        initial_priority = 1
        initial_desc = "AI is currently analyzing the uploaded image(s) and classifying the hazard..."
        
        cursor.execute("""
        INSERT INTO reports (
            id, latitude, longitude, image_path, tags, department, priority, 
            votes, status, created_at, updated_at, reporter_email, reporter_name, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, latitude, longitude, db_image_path_str, json.dumps(initial_tags), 
            initial_dept, initial_priority, 1, status, now_str, now_str, 
            reporter_email, reporter_name, initial_desc
        ))
        
        # Enqueue background processing task
        background_tasks.add_task(async_process_report_ai, report_id, final_db_paths, user_note, latitude, longitude)
        
        tags_return = initial_tags
        dept_return = initial_dept
        priority_return = initial_priority
    else:
        # Synchronous path (e.g. from existing test suites or direct manual submission)
        status = "Pending"
        try:
            tags_list = json.loads(tags)
        except Exception:
            tags_list = [tags]
            
        # Basic clustering: If any open report is within 75 meters (0.075 km), link it
        cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved'")
        active_reports = cursor.fetchall()
        
        priority_bonus = 0
        for rep in active_reports:
            dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
            if dist <= 0.075: # 75 meters
                priority_bonus += 1
                cursor.execute("UPDATE reports SET votes = votes + 1 WHERE id = ?", (rep["id"],))
                
        final_priority = min(5, priority + priority_bonus)
        
        cursor.execute("""
        INSERT INTO reports (
            id, latitude, longitude, image_path, tags, department, priority, 
            votes, status, created_at, updated_at, reporter_email, reporter_name, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, latitude, longitude, db_image_path_str, json.dumps(tags_list), 
            department, final_priority, 1, status, now_str, now_str, 
            reporter_email, reporter_name, description or "No description provided."
        ))
        
        tags_return = tags_list
        dept_return = department
        priority_return = final_priority

    # Upsert leaderboard info
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
        ON CONFLICT (email) DO NOTHING
        """, (reporter_email, reporter_name, reporter_avatar))
        
    # Link QR session if token is provided
    if token:
        cursor.execute("UPDATE qr_sessions SET status = 'uploaded', associated_report_id = ? WHERE token = ?", (report_id, token))
        
    conn.commit()
    conn.close()
    
    return {
        "id": report_id, 
        "status": status, 
        "tags": tags_return, 
        "department": dept_return, 
        "priority": priority_return
    }

@app.post("/api/reports/vote/{id}")
async def vote_report(id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT votes, priority FROM reports WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
    
    new_votes = row["votes"] + 1
    # Simple threshold escalation: every 5 votes adds +1 priority level, max 5
    new_priority = min(5, row["priority"] + (1 if new_votes % 5 == 0 else 0))
    
    cursor.execute("UPDATE reports SET votes = ?, priority = ? WHERE id = ?", (new_votes, new_priority, id))
    conn.commit()
    conn.close()
    return {"id": id, "votes": new_votes, "priority": new_priority}

@app.get("/api/reports/list")
async def list_reports():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/reports/track/{id}")
async def track_report(id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(row)

@app.get("/api/leaderboard")
async def get_leaderboard():
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leaderboard ORDER BY civic_points DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/reports/my-reports/{email}")
async def get_my_reports(email: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE reporter_email = ? ORDER BY created_at DESC", (email,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

from pydantic import BaseModel
from typing import Optional

class CreateSessionRequest(BaseModel):
    reporter_email: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_avatar: Optional[str] = None

# QR Session API endpoints for Cross-Device upload
@app.post("/api/sessions/create")
async def create_session(req: Optional[CreateSessionRequest] = None):
    token = str(uuid.uuid4())
    conn = database.get_db()
    cursor = conn.cursor()
    draft_json = None
    if req:
        draft_json = json.dumps({
            "reporter_email": req.reporter_email,
            "reporter_name": req.reporter_name,
            "reporter_avatar": req.reporter_avatar
        })
    cursor.execute("INSERT INTO qr_sessions (token, status, created_at, draft_data) VALUES (?, 'pending', ?, ?)", (token, datetime.now(timezone.utc).isoformat(), draft_json))
    conn.commit()
    conn.close()
    return {"token": token}

@app.get("/api/sessions/status/{token}")
async def get_session_status(token: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status, associated_report_id, draft_data FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    res = dict(row)
    if res.get("draft_data"):
        res["draft_data"] = json.loads(res["draft_data"])
    return res

def async_process_draft_ai(token: str, final_db_paths: list, latitude: float, longitude: float, reporter_email: str, reporter_name: str, reporter_avatar: str):
    images_bytes = []
    for path in final_db_paths:
        if path.startswith("data:image/"):
            try:
                header, encoded = path.split(",", 1)
                images_bytes.append(base64.b64decode(encoded))
            except Exception as e:
                print(f"Failed to decode base64 image in async_process_draft_ai: {e}")
        else:
            local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1) if path.startswith("/uploads/") else path
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        images_bytes.append(f.read())
                except Exception as e:
                    print(f"Failed to read image {local_path}: {e}")
                
    try:
        ai_data = gemini_service.analyze_report_images(images_bytes)
        
        draft_meta = {
            "image_path": json.dumps(final_db_paths),
            "latitude": latitude,
            "longitude": longitude,
            "tags": ai_data.get("tags", ["Pothole"]),
            "department": ai_data.get("department", "Municipal Roads"),
            "priority": ai_data.get("priority", 3),
            "analysis": ai_data.get("analysis", "AI classified this draft report."),
            "reporter_email": reporter_email,
            "reporter_name": reporter_name,
            "reporter_avatar": reporter_avatar
        }
        
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE qr_sessions SET status = 'draft', draft_data = ? WHERE token = ?",
            (json.dumps(draft_meta), token)
        )
        conn.commit()
        conn.close()
        print(f"Draft session {token} processed by AI and set to draft.")
    except Exception as e:
        print(f"Error in background AI analysis for draft session {token}: {e}")

@app.post("/api/sessions/upload/{token}")
async def upload_session_photo(
    token: str,
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status, draft_data FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Update status to processing
    cursor.execute("UPDATE qr_sessions SET status = 'processing' WHERE token = ?", (token,))
    conn.commit()
    
    # Gather uploaded files
    uploaded_files = []
    if images:
        uploaded_files = images
    elif image:
        uploaded_files = [image]
        
    if not uploaded_files:
        conn.close()
        raise HTTPException(status_code=400, detail="No images uploaded")
        
    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    final_db_paths = []
    
    # Save files using aiofiles
    for idx, file in enumerate(uploaded_files):
        contents = await file.read()
        filename = f"{report_id}_before_{idx}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(contents)
        
        # Convert to base64
        encoded = base64.b64encode(contents).decode("utf-8")
        base64_url = f"data:image/jpeg;base64,{encoded}"
        final_db_paths.append(base64_url)
        
    # Determine reporter settings from draft_data
    reporter_email = "anonymous@civicfix.org"
    reporter_name = "Anonymous"
    reporter_avatar = "https://api.dicebear.com/7.x/bottts/svg?seed=anonymous"
    
    if row["draft_data"]:
        try:
            meta = json.loads(row["draft_data"])
            if meta.get("reporter_email"):
                reporter_email = meta["reporter_email"]
            if meta.get("reporter_name"):
                reporter_name = meta["reporter_name"]
            if meta.get("reporter_avatar"):
                reporter_avatar = meta["reporter_avatar"]
        except Exception:
            pass
            
    conn.close()
    
    # Enqueue background task to perform diagnostics and set session to draft
    background_tasks.add_task(
        async_process_draft_ai, 
        token, final_db_paths, latitude, longitude, 
        reporter_email, reporter_name, reporter_avatar
    )
    
    return {"status": "processing"}

@app.post("/api/reports/resolve/{id}")
async def resolve_report(id: str, resolved_image: UploadFile = File(...)):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT image_path FROM reports WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
    
    before_filepath_raw = row["image_path"]
    try:
        paths = json.loads(before_filepath_raw)
        if isinstance(paths, list) and len(paths) > 0:
            before_filepath = paths[0]
        else:
            before_filepath = before_filepath_raw
    except Exception:
        before_filepath = before_filepath_raw

    # Save resolved image
    after_contents = await resolved_image.read()
    resolved_filename = f"{id}_after.jpg"
    after_filepath = os.path.join(UPLOAD_DIR, resolved_filename)
    async with aiofiles.open(after_filepath, "wb") as f:
        await f.write(after_contents)

    if before_filepath.startswith("data:image/"):
        try:
            header, encoded = before_filepath.split(",", 1)
            before_contents = base64.b64decode(encoded)
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Failed to decode base64 before image: {e}")
    else:
        if before_filepath.startswith("/uploads/"):
            before_filepath = before_filepath.replace("/uploads/", f"{UPLOAD_DIR}/", 1)
            
        # Secure path traversal check
        base_dir = Path(UPLOAD_DIR)
        before_path = Path(before_filepath)
        if not is_safe_path(base_dir, before_path):
            conn.close()
            raise HTTPException(status_code=400, detail="Access denied")
        resolved_before = str(before_path.resolve())
            
        # Read before image bytes
        async with aiofiles.open(resolved_before, "rb") as f:
            before_contents = await f.read()
        
    # Verify resolution using Gemini Vision
    verify_data = gemini_service.verify_resolution(before_contents, after_contents)
    
    if verify_data["verified"]:
        now_str = datetime.now(timezone.utc).isoformat()
        # Convert resolved image to base64
        encoded_after = base64.b64encode(after_contents).decode("utf-8")
        db_resolved_path = f"data:image/jpeg;base64,{encoded_after}"
        cursor.execute("""
        UPDATE reports 
        SET status = 'Resolved', resolved_image_path = ?, updated_at = ? 
        WHERE id = ?
        """, (db_resolved_path, now_str, id))
        conn.commit()
    
    conn.close()
    return verify_data

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Expose uploaded images
app.mount("/tmp/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads_tmp")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

TEMPLATES = {}
for name in ["dashboard.html", "map.html", "report.html", "leaderboard.html"]:
    path = os.path.join("templates", name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            TEMPLATES[name] = f.read()
    else:
        TEMPLATES[name] = f"Template {name} not found"

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTMLResponse(content=TEMPLATES.get("dashboard.html", ""))

@app.get("/map", response_class=HTMLResponse)
async def serve_map():
    return HTMLResponse(content=TEMPLATES.get("map.html", ""))

@app.get("/report", response_class=HTMLResponse)
async def serve_report():
    return HTMLResponse(content=TEMPLATES.get("report.html", ""))

@app.get("/leaderboard", response_class=HTMLResponse)
async def serve_leaderboard():
    return HTMLResponse(content=TEMPLATES.get("leaderboard.html", ""))

