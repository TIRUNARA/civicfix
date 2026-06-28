from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import database
import gemini_service
import uuid
import math
import os
from datetime import datetime, timezone
import json
from typing import List, Optional
import aiofiles
from pathlib import Path
import base64
import html
import time
from collections import defaultdict

# Secure custom in-memory rate limiter with zero external dependencies
class SimpleRateLimiter:
    def __init__(self, requests_limit: int, window_seconds: int):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < self.window_seconds]
        if len(self.history[client_ip]) >= self.requests_limit:
            return False
        self.history[client_ip].append(now)
        return True

submit_limiter = SimpleRateLimiter(requests_limit=20, window_seconds=60)

def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    try:
        resolved_base = base_dir.resolve()
        resolved_target = target_path.resolve()
        return resolved_target == resolved_base or resolved_base in resolved_target.parents
    except Exception:
        return False

app = FastAPI(title="CivicFix Core")

# Configure CORS dynamically from ALLOWED_ORIGINS env var with safe defaults
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://127.0.0.1:5500")
origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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

# Health check route
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected"
    }

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
                
    conn = None
    try:
        ai_data = gemini_service.analyze_report_images(images_bytes, user_note, latitude, longitude)
        tags_list = ai_data.get("tags", ["unknown"])
        dept = ai_data.get("department", "Other Issues")
        priority = ai_data.get("priority", 1)
        description = ai_data.get("analysis", "No description provided.")
        clarification_requested = ai_data.get("clarification_requested", False)
        
        status = "Clarification Needed" if clarification_requested else "Pending"
        if clarification_requested and "suggested_action" in ai_data:
            description = ai_data["suggested_action"]
            
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
            SET tags = ?, department = ?, priority = ?, description = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(tags_list),
            dept,
            final_priority,
            description,
            status,
            datetime.now(timezone.utc).isoformat(),
            report_id
        ))
        
        cursor.execute("DELETE FROM report_approvals WHERE report_id = ?", (report_id,))
        depts = [d.strip() for d in dept.split(",") if d.strip()]
        for d in depts:
            cursor.execute("""
                INSERT OR IGNORE INTO report_approvals (report_id, department, status)
                VALUES (?, ?, 'Pending')
            """, (report_id, d))
            
        conn.commit()
        print(f"Background AI processing succeeded for report {report_id} -> {status}")
    except Exception as e:
        print(f"Error in background AI analysis for {report_id}: {e}")
        try:
            if not conn:
                conn = database.get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reports SET status = 'Failed', description = ? WHERE id = ?",
                (f"AI processing failed: {str(e)[:200]}", report_id)
            )
            conn.commit()
        except Exception as db_err:
            print(f"Failed to write failure status to DB: {db_err}")
    finally:
        if conn:
            conn.close()

@app.post("/api/reports/analyze")
async def analyze_photo(
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None),
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
    request: Request,
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(None),
    image: UploadFile = File(None),
    image_path: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    tags: str = Form(None),
    department: str = Form(None),
    priority: int = Form(None),
    description: str = Form(None),
    user_note: str = Form(None),
    reporter_email: str = Form("anonymous@civicfix.org"),
    reporter_name: str = Form("Anonymous"),
    reporter_avatar: str = Form(""),
    token: str = Form(None)
):
    # Enforce Rate Limiting
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not submit_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # Sanitize HTML tags from inputs to prevent injection/XSS
    user_note_clean = html.escape(user_note) if user_note else None
    desc_clean = html.escape(description) if description else None
    reporter_email_clean = html.escape(reporter_email) if reporter_email else "anonymous@civicfix.org"
    reporter_name_clean = html.escape(reporter_name) if reporter_name else "Anonymous"

    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    final_db_paths = []
    
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
            
            encoded = base64.b64encode(contents).decode("utf-8")
            base64_url = f"data:image/jpeg;base64,{encoded}"
            final_db_paths.append(base64_url)
            
    elif image_path:
        try:
            paths = json.loads(image_path)
            if not isinstance(paths, list):
                paths = [image_path]
        except Exception:
            paths = [image_path]
            
        base_dir = Path(UPLOAD_DIR)
        for idx, path_str in enumerate(paths):
            if path_str.startswith("data:image/"):
                final_db_paths.append(path_str)
            else:
                local_path = path_str.replace("/uploads/", f"{UPLOAD_DIR}/", 1) if path_str.startswith("/uploads/") else path_str
                path_obj = Path(local_path)
                if not is_safe_path(base_dir, path_obj):
                    raise HTTPException(status_code=400, detail="Access denied")
                resolved_path = str(path_obj.resolve())
                    
                if not os.path.exists(resolved_path):
                    raise HTTPException(status_code=404, detail=f"Draft image not found: {path_str}")
                    
                filename = f"{report_id}_before_{idx}.jpg"
                filepath = os.path.join(UPLOAD_DIR, filename)
                async with aiofiles.open(resolved_path, "rb") as src:
                    src_contents = await src.read()
                async with aiofiles.open(filepath, "wb") as dst:
                    await dst.write(src_contents)
                
                encoded = base64.b64encode(src_contents).decode("utf-8")
                base64_url = f"data:image/jpeg;base64,{encoded}"
                final_db_paths.append(base64_url)
    else:
        raise HTTPException(status_code=400, detail="No images provided")
        
    db_image_path_str = json.dumps(final_db_paths)
    now_str = datetime.now(timezone.utc).isoformat()
    
    conn = database.get_db()
    cursor = conn.cursor()
    
    is_async = tags is None or department is None or priority is None
    
    if is_async:
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
            reporter_email_clean, reporter_name_clean, initial_desc
        ))
        
        background_tasks.add_task(async_process_report_ai, report_id, final_db_paths, user_note_clean, latitude, longitude)
        
        tags_return = initial_tags
        dept_return = initial_dept
        priority_return = initial_priority
    else:
        status = "Pending"
        try:
            tags_list = json.loads(tags)
        except Exception:
            tags_list = [tags]
            
        cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved'")
        active_reports = cursor.fetchall()
        
        priority_bonus = 0
        for rep in active_reports:
            dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
            if dist <= 0.075:
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
            reporter_email_clean, reporter_name_clean, desc_clean or "No description provided."
        ))
        
        depts = [d.strip() for d in department.split(",") if d.strip()]
        for d in depts:
            cursor.execute("""
                INSERT OR IGNORE INTO report_approvals (report_id, department, status)
                VALUES (?, ?, 'Pending')
            """, (report_id, d))
            
        tags_return = tags_list
        dept_return = department
        priority_return = final_priority

    # Idempotent Atomic Upsert to prevent race conditions
    cursor.execute("""
        INSERT INTO leaderboard (email, username, avatar_url, civic_points, reports_submitted)
        VALUES (?, ?, ?, 10, 1)
        ON CONFLICT(email) DO UPDATE SET
            civic_points = leaderboard.civic_points + 10,
            reports_submitted = leaderboard.reports_submitted + 1,
            username = excluded.username,
            avatar_url = excluded.avatar_url
    """, (reporter_email_clean, reporter_name_clean, reporter_avatar))
        
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
    new_priority = min(5, row["priority"] + (1 if new_votes % 5 == 0 else 0))
    
    cursor.execute("UPDATE reports SET votes = ?, priority = ? WHERE id = ?", (new_votes, new_priority, id))
    conn.commit()
    conn.close()
    return {"id": id, "votes": new_votes, "priority": new_priority}

@app.get("/api/reports/list")
async def list_reports(role: str = "citizen", email: str = None, user_id: str = None):
    conn = database.get_db()
    cursor = conn.cursor()
    
    dept_filter = None
    if email:
        email_lower = email.lower()
        if "road" in email_lower:
            dept_filter = "Municipal Roads"
        elif "water" in email_lower or "sanit" in email_lower:
            dept_filter = "Water & Sanitation"
        elif "elect" in email_lower or "light" in email_lower or "power" in email_lower or "street" in email_lower:
            dept_filter = "Utility Streetlighting"
        elif "garbage" in email_lower or "solid" in email_lower:
            dept_filter = "Solid Waste"
        elif "park" in email_lower or "garden" in email_lower:
            dept_filter = "Parks"
        elif "highway" in email_lower or "national" in email_lower:
            dept_filter = "National Highways"
        elif "grid" in email_lower or "state" in email_lower:
            dept_filter = "State Grid"
        elif "environ" in email_lower:
            dept_filter = "Environment Board"

    if role == "citizen":
        cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
        rows = cursor.fetchall()
    elif role == "officer":
        if dept_filter:
            cursor.execute(
                "SELECT * FROM reports WHERE department LIKE ? ORDER BY created_at DESC",
                (f"%{dept_filter}%",)
            )
        else:
            # Fallback: officer without recognizable dept keyword — show all
            cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
        rows = cursor.fetchall()
    elif role == "reviewer":
        if user_id:
            cursor.execute("""
                SELECT DISTINCT r.* FROM reports r
                LEFT JOIN reviewer_assignments ra ON r.id = ra.report_id
                WHERE ra.reviewer_id = ?
                ORDER BY r.created_at DESC
            """, (user_id,))
        elif dept_filter:
            cursor.execute(
                "SELECT * FROM reports WHERE department LIKE ? ORDER BY created_at DESC",
                (f"%{dept_filter}%",)
            )
        else:
            cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
        rows = cursor.fetchall()
    elif role == "fixer":
        if user_id:
            cursor.execute("""
                SELECT DISTINCT r.* FROM reports r
                LEFT JOIN fixer_assignments fa ON r.id = fa.report_id
                WHERE fa.fixer_id = ?
                ORDER BY r.created_at DESC
            """, (user_id,))
        elif dept_filter:
            cursor.execute(
                "SELECT * FROM reports WHERE department LIKE ? ORDER BY created_at DESC",
                (f"%{dept_filter}%",)
            )
        else:
            cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
        rows = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
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

@app.get("/api/reports/timeline/{id}")
async def get_report_timeline(id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM reports WHERE id = ?", (id,))
    r = cursor.fetchone()
    if not r:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
    
    events = []
    
    # 1. Submission
    events.append({
        "title": "Report Submitted",
        "description": f"Citizen logged hazard ticket. Original Priority Lvl: {r['priority']}.",
        "timestamp": r["created_at"],
        "status": "completed",
        "epoch": r["created_at"]
    })
    
    # 2. AI Routing
    events.append({
        "title": "AI Routing Completed",
        "description": f"CivicFix AI analyzed tags {r['tags']} and routed report to: {r['department']}.",
        "timestamp": r["created_at"], # AI routing is instant
        "status": "completed",
        "epoch": r["created_at"]
    })
    
    # 3. Department Approvals
    cursor.execute("SELECT * FROM report_approvals WHERE report_id = ?", (id,))
    approvals = cursor.fetchall()
    for app in approvals:
        is_approved = app["status"] == "Approved"
        events.append({
            "title": f"Approval: {app['department']}",
            "description": f"Status: {app['status']} " + (f"by {app['officer_email']}" if is_approved else "(Awaiting validation)"),
            "timestamp": app["approved_at"] if app["approved_at"] else "Awaiting action",
            "status": "completed" if is_approved else "active",
            "epoch": app["approved_at"] if app["approved_at"] else "9999-12-31"
        })
        
    # 4. Reviewer diagnostics
    cursor.execute("SELECT * FROM reviewer_assignments WHERE report_id = ?", (id,))
    revs = cursor.fetchall()
    for rv in revs:
        is_done = rv["status"] == "Completed" or rv["completed_at"] is not None
        events.append({
            "title": f"Field Audit: {rv['department']}",
            "description": f"Reviewer {rv['reviewer_id']} audit: " + (f"Complete. Resources logged: {rv['resources_logged']}. Location: {rv['end_latitude']}, {rv['end_longitude']}." if is_done else "Dispatched to site."),
            "timestamp": rv["completed_at"] if rv["completed_at"] else "In progress",
            "status": "completed" if is_done else "active",
            "epoch": rv["completed_at"] if rv["completed_at"] else "9999-12-31"
        })
        
    # 5. Fixer dispatches
    cursor.execute("SELECT * FROM fixer_assignments WHERE report_id = ?", (id,))
    fixes = cursor.fetchall()
    for fx in fixes:
        is_done = fx["status"] == "Completed" or fx["completed_at"] is not None
        events.append({
            "title": f"Repair Dispatch: {fx['department']}",
            "description": f"Ground crew {fx['fixer_id']} assigned. Status: {fx['status']}.",
            "timestamp": fx["completed_at"] if fx["completed_at"] else "Dispatched / fixing",
            "status": "completed" if is_done else "active",
            "epoch": fx["completed_at"] if fx["completed_at"] else "9999-12-31"
        })
        
    # 6. Final resolution
    if r["status"] == "Resolved":
        events.append({
            "title": "Resolution Verified",
            "description": "Officer verified completion image. Ticket closed successfully.",
            "timestamp": r["updated_at"],
            "status": "completed",
            "epoch": r["updated_at"]
        })
    
    # Sort events by timestamp (completed first, then active/pending)
    events.sort(key=lambda x: x["epoch"])
    
    # Clean epochs from return
    for ev in events:
        ev.pop("epoch", None)
        
    conn.close()
    return events

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

class ApproveRequest(BaseModel):
    department: str
    officer_email: str

class ReviewerAnalysisRequest(BaseModel):
    report_id: str
    reviewer_id: str
    resources_logged: str
    end_latitude: float
    end_longitude: float
    analysis_image: Optional[str] = None

class CoordinationMessageRequest(BaseModel):
    report_id: str
    sender_id: str
    sender_name: str
    sender_role: str
    message: str

class FixerStartWorkRequest(BaseModel):
    report_id: str
    fixer_id: str

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
                
    conn = None
    try:
        ai_data = gemini_service.analyze_report_images(images_bytes, None, latitude, longitude)
        
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
        print(f"Draft session {token} processed by AI and set to draft.")
    except Exception as e:
        print(f"Error in background AI analysis for draft session {token}: {e}")
        try:
            if not conn:
                conn = database.get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE qr_sessions SET status = 'failed' WHERE token = ?",
                (token,)
            )
            conn.commit()
        except Exception as db_err:
            print(f"Failed to write draft failure status to DB: {db_err}")
    finally:
        if conn:
            conn.close()

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
        encoded_after = base64.b64encode(after_contents).decode("utf-8")
        db_resolved_path = f"data:image/jpeg;base64,{encoded_after}"
        cursor.execute("""
        UPDATE reports 
        SET status = 'Resolved', resolved_image_path = ?, updated_at = ? 
        WHERE id = ?
        """, (db_resolved_path, now_str, id))
        
        # Free up assigned fixers
        cursor.execute("SELECT fixer_id FROM fixer_assignments WHERE report_id = ?", (id,))
        assigned_fixers = cursor.fetchall()
        for fixer in assigned_fixers:
            cursor.execute("UPDATE fixers SET is_available = 1 WHERE id = ?", (fixer["fixer_id"],))
            
        conn.commit()
    
    conn.close()
    return verify_data

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
@app.get("/dashboard", response_class=HTMLResponse)
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

# --- Segment 1/2/3/4 Orchestration Helpers & Endpoints ---

async def trigger_reviewer_assignment(report_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Get report location and departments
    cursor.execute("SELECT latitude, longitude, department FROM reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        return
        
    lat, lon, dept_str = report["latitude"], report["longitude"], report["department"]
    depts = [d.strip() for d in dept_str.split(",") if d.strip()]
    
    for dept in depts:
        # Find available reviewers in this department
        cursor.execute("SELECT id, latitude, longitude FROM reviewers WHERE department = ? AND is_available = 1", (dept,))
        reviewers = cursor.fetchall()
        
        if not reviewers:
            continue
            
        # Find nearest reviewer
        nearest_reviewer = None
        min_dist = float("inf")
        for rev in reviewers:
            dist = get_distance(lat, lon, rev["latitude"], rev["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest_reviewer = rev
                
        if nearest_reviewer:
            # Create reviewer assignment
            cursor.execute("""
                INSERT INTO reviewer_assignments (report_id, reviewer_id, department, status)
                VALUES (?, ?, ?, 'Assigned')
            """, (report_id, nearest_reviewer["id"], dept))
            
            # Mark reviewer unavailable
            cursor.execute("UPDATE reviewers SET is_available = 0 WHERE id = ?", (nearest_reviewer["id"],))
            
    conn.commit()
    conn.close()

async def trigger_fixer_dispatch(report_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT department FROM reports WHERE id = ?", (report_id,))
    report = cursor.fetchone()
    if not report:
        conn.close()
        return
        
    dept_str = report["department"]
    depts = [d.strip() for d in dept_str.split(",") if d.strip()]
    
    is_coordinated = 1 if len(depts) > 1 else 0
    
    for dept in depts:
        # Find available fixer in this department
        cursor.execute("SELECT id FROM fixers WHERE department = ? AND is_available = 1 LIMIT 1", (dept,))
        fixer = cursor.fetchone()
        if fixer:
            cursor.execute("""
                INSERT INTO fixer_assignments (report_id, fixer_id, department, status)
                VALUES (?, ?, ?, 'Assigned')
            """, (report_id, fixer["id"], dept))
            
            cursor.execute("UPDATE fixers SET is_available = 0 WHERE id = ?", (fixer["id"],))
            
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE reports SET status = 'Fixing', is_coordinated = ?, updated_at = ? WHERE id = ?", (is_coordinated, now_str, report_id))
    conn.commit()
    conn.close()

@app.get("/api/reports/approvals/{id}")
async def get_report_approvals(id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM report_approvals WHERE report_id = ?", (id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/reports/approve/{id}")
async def approve_report(id: str, req: ApproveRequest):
    conn = database.get_db()
    cursor = conn.cursor()
    
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("SELECT 1 FROM report_approvals WHERE report_id = ? AND department = ?", (id, req.department))
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute("""
            INSERT INTO report_approvals (report_id, department, status, officer_email, approved_at)
            VALUES (?, ?, 'Approved', ?, ?)
        """, (id, req.department, req.officer_email, now_str))
    else:
        cursor.execute("""
            UPDATE report_approvals 
            SET status = 'Approved', officer_email = ?, approved_at = ?
            WHERE report_id = ? AND department = ?
        """, (req.officer_email, now_str, id, req.department))
        
    # 2. Check if all departments for this report have approved
    cursor.execute("SELECT status FROM report_approvals WHERE report_id = ?", (id,))
    all_approvals = cursor.fetchall()
    
    all_approved = all([r["status"] == "Approved" for r in all_approvals])
    
    if all_approved and len(all_approvals) > 0:
        # Transition status to Segment 2
        cursor.execute("UPDATE reports SET status = 'Reviewing', updated_at = ? WHERE id = ?", (now_str, id))
        conn.commit()
        conn.close()
        
        # TRIGGER Dynamic Reviewer Assignment
        await trigger_reviewer_assignment(id)
        return {"status": "Reviewing", "message": "All departments approved. Reviewers assigned."}
        
    conn.commit()
    conn.close()
    return {"status": "Pending", "message": f"Department {req.department} approved. Waiting for others."}

@app.get("/api/reviewer/assignments/{report_id}")
async def get_reviewer_assignments(report_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ra.*, r.name as reviewer_name FROM reviewer_assignments ra JOIN reviewers r ON ra.reviewer_id = r.id WHERE ra.report_id = ?", (report_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/reviewer/upload-image")
async def reviewer_upload_image(image: UploadFile = File(...)):
    filename = f"reviewer_{int(time.time())}_{image.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(await image.read())
    return {"image_path": f"/uploads/{filename}"}

@app.post("/api/reviewer/submit-analysis")
async def submit_reviewer_analysis(req: ReviewerAnalysisRequest):
    conn = database.get_db()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    
    # 1. Update the reviewer assignment
    cursor.execute("""
        UPDATE reviewer_assignments
        SET status = 'Completed', resources_logged = ?, completed_at = ?, end_latitude = ?, end_longitude = ?, analysis_image = ?
        WHERE report_id = ? AND reviewer_id = ?
    """, (req.resources_logged, now_str, req.end_latitude, req.end_longitude, req.analysis_image, req.report_id, req.reviewer_id))
    
    # 2. Update reviewer location and availability
    cursor.execute("""
        UPDATE reviewers
        SET latitude = ?, longitude = ?, is_available = 1
        WHERE id = ?
    """, (req.end_latitude, req.end_longitude, req.reviewer_id))
    
    # 3. Check if all reviewers for this report are completed
    cursor.execute("SELECT status FROM reviewer_assignments WHERE report_id = ?", (req.report_id,))
    all_assignments = cursor.fetchall()
    
    all_completed = all([a["status"] == "Completed" for a in all_assignments])
    
    if all_completed and len(all_assignments) > 0:
        # Transition status to Segment 3
        cursor.execute("UPDATE reports SET status = 'Fixer Dispatch', updated_at = ? WHERE id = ?", (now_str, req.report_id))
        conn.commit()
        conn.close()
        
        # TRIGGER Actual Fixer Dispatch
        await trigger_fixer_dispatch(req.report_id)
        return {"status": "Fixing", "message": "All reviews complete. Ground crews dispatched."}
        
    conn.commit()
    conn.close()
    return {"status": "Reviewing", "message": f"Review by {req.reviewer_id} submitted."}

@app.get("/api/fixer/assignments/{report_id}")
async def get_fixer_assignments(report_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fa.*, f.name as fixer_name FROM fixer_assignments fa JOIN fixers f ON fa.fixer_id = f.id WHERE fa.report_id = ?", (report_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/coordination/get-messages/{report_id}")
async def get_coordination_messages(report_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coordination_messages WHERE report_id = ? ORDER BY id ASC", (report_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/coordination/send-message")
async def send_coordination_message(req: CoordinationMessageRequest):
    conn = database.get_db()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
        INSERT INTO coordination_messages (report_id, sender_id, sender_name, sender_role, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (req.report_id, req.sender_id, req.sender_name, req.sender_role, req.message, now_str))
    
    conn.commit()
    conn.close()
    return {"status": "sent"}

@app.post("/api/fixer/start-work")
async def fixer_start_work(req: FixerStartWorkRequest):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE fixer_assignments 
        SET status = 'Work in Progress' 
        WHERE report_id = ? AND fixer_id = ?
    """, (req.report_id, req.fixer_id))
    
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE reports 
        SET status = 'Work in Progress', updated_at = ? 
        WHERE id = ?
    """, (now_str, req.report_id))
    
    conn.commit()
    conn.close()
    return {"status": "Work in Progress", "message": "Work started successfully."}
