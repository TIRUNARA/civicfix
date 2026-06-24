from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import database
import gemini_service
import uuid
import math
import os
from datetime import datetime
import json

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
os.makedirs("/tmp/uploads", exist_ok=True)
database.init_db()

# Haversine distance formula (in km)
def get_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.post("/api/reports/analyze")
async def analyze_photo(image: UploadFile = File(...)):
    contents = await image.read()
    ai_data = gemini_service.analyze_report_image(contents)
    return ai_data

@app.post("/api/reports/submit")
async def submit_report(
    image: UploadFile = File(None),
    image_path: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    tags: str = Form(...), # JSON serialized tags list
    department: str = Form(...),
    priority: int = Form(...),
    description: str = Form(...),
    reporter_email: str = Form("anonymous@civicfix.org"),
    reporter_name: str = Form("Anonymous"),
    reporter_avatar: str = Form(""),
    token: str = Form(None) # Optional QR session token to link
):
    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    filename = f"{report_id}_before.jpg"
    filepath = os.path.join("/tmp/uploads", filename)
    
    if image:
        contents = await image.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    elif image_path:
        # Secure path checking
        if not os.path.abspath(image_path).startswith("/tmp/uploads/"):
            raise HTTPException(status_code=400, detail="Invalid image path")
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Draft image not found")
        # Copy the temporary draft image to the final location
        with open(image_path, "rb") as src, open(filepath, "wb") as dst:
            dst.write(src.read())
    else:
        raise HTTPException(status_code=400, detail="No image provided")
        
    try:
        tags_list = json.loads(tags)
    except Exception:
        tags_list = [tags]
        
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Basic clustering: If any open report is within 75 meters (0.075 km), link it
    cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved'")
    active_reports = cursor.fetchall()
    
    priority_bonus = 0
    for rep in active_reports:
        dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
        if dist <= 0.075: # 75 meters
            priority_bonus += 1
            # Auto-upvote adjacent issue
            cursor.execute("UPDATE reports SET votes = votes + 1 WHERE id = ?", (rep["id"],))
            
    final_priority = min(5, priority + priority_bonus)
    now_str = datetime.utcnow().isoformat()
    
    # Insert report with reporter context
    cursor.execute("""
    INSERT INTO reports (
        id, latitude, longitude, image_path, tags, department, priority, 
        votes, status, created_at, updated_at, reporter_email, reporter_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, latitude, longitude, filepath, json.dumps(tags_list), 
        department, final_priority, 1, "Reported", now_str, now_str, 
        reporter_email, reporter_name
    ))
    
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
        """, (reporter_email, reporter_name, reporter_avatar))
        
    # Link QR session if token is provided
    if token:
        cursor.execute("UPDATE qr_sessions SET status = 'uploaded', associated_report_id = ? WHERE token = ?", (report_id, token))
        
    conn.commit()
    conn.close()
    
    return {
        "id": report_id, 
        "status": "Reported", 
        "tags": tags_list, 
        "department": department, 
        "priority": final_priority
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

# QR Session API endpoints for Cross-Device upload
@app.post("/api/sessions/create")
async def create_session():
    token = str(uuid.uuid4())
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO qr_sessions (token, status, created_at) VALUES (?, 'pending', ?)", (token, datetime.utcnow().isoformat()))
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

@app.post("/api/sessions/upload/{token}")
async def upload_session_photo(
    token: str,
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    contents = await image.read()
    filename = f"draft_{token}.jpg"
    filepath = os.path.join("/tmp/uploads", filename)
    with open(filepath, "wb") as f:
        f.write(contents)
        
    # Analyze the photo via Gemini
    ai_data = gemini_service.analyze_report_image(contents)
    
    # Store draft details
    draft_data = {
        "image_path": f"/tmp/uploads/{filename}",
        "latitude": latitude,
        "longitude": longitude,
        "tags": ai_data["tags"],
        "department": ai_data["department"],
        "priority": ai_data["priority"],
        "analysis": ai_data["analysis"]
    }
    
    cursor.execute(
        "UPDATE qr_sessions SET status = 'draft', draft_data = ? WHERE token = ?",
        (json.dumps(draft_data), token)
    )
    conn.commit()
    conn.close()
    
    return {"status": "draft", "draft_data": draft_data}

@app.post("/api/reports/resolve/{id}")
async def resolve_report(id: str, resolved_image: UploadFile = File(...)):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT image_path FROM reports WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")
    
    before_filepath = row["image_path"]
    
    # Save resolved image
    after_contents = await resolved_image.read()
    resolved_filename = f"{id}_after.jpg"
    after_filepath = os.path.join("/tmp/uploads", resolved_filename)
    with open(after_filepath, "wb") as f:
        f.write(after_contents)
        
    # Read before image bytes
    with open(before_filepath, "rb") as f:
        before_contents = f.read()
        
    # Verify resolution using Gemini Vision
    verify_data = gemini_service.verify_resolution(before_contents, after_contents)
    
    if verify_data["verified"]:
        now_str = datetime.utcnow().isoformat()
        cursor.execute("""
        UPDATE reports 
        SET status = 'Resolved', resolved_image_path = ?, updated_at = ? 
        WHERE id = ?
        """, (after_filepath, now_str, id))
        conn.commit()
    
    conn.close()
    return verify_data

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Expose uploaded images
app.mount("/tmp/uploads", StaticFiles(directory="/tmp/uploads"), name="uploads")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())
