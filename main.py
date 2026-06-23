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

@app.post("/api/reports/submit")
async def submit_report(
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    username: str = Form("Anonymous")
):
    contents = await image.read()
    report_id = f"CF-{uuid.uuid4().hex[:6].upper()}"
    filename = f"{report_id}_before.jpg"
    filepath = os.path.join("/tmp/uploads", filename)
    with open(filepath, "wb") as f:
        f.write(contents)
        
    # Analyze photo via Gemini
    ai_data = gemini_service.analyze_report_image(contents)
    
    # Basic clustering: If any open report is within 75 meters (0.075 km), link it
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, latitude, longitude, priority, votes FROM reports WHERE status != 'Resolved'")
    active_reports = cursor.fetchall()
    
    priority_bonus = 0
    for rep in active_reports:
        dist = get_distance(latitude, longitude, rep["latitude"], rep["longitude"])
        if dist <= 0.075: # 75 meters
            priority_bonus += 1
            # Auto-upvote adjacent issue
            cursor.execute("UPDATE reports SET votes = votes + 1 WHERE id = ?", (rep["id"],))
            
    conn.commit()
    
    # Calculate scaled priority
    final_priority = min(5, ai_data["priority"] + priority_bonus)
    now_str = datetime.utcnow().isoformat()
    
    # Insert report
    cursor.execute("""
    INSERT INTO reports (id, latitude, longitude, image_path, tags, department, priority, votes, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, latitude, longitude, filepath, json.dumps(ai_data["tags"]), ai_data["department"], final_priority, 1, "Reported", now_str, now_str))
    
    # Update leaderboard
    cursor.execute("INSERT OR IGNORE INTO leaderboard (username, civic_points, reports_submitted) VALUES (?, 0, 0)", (username,))
    cursor.execute("UPDATE leaderboard SET civic_points = civic_points + 10, reports_submitted = reports_submitted + 1 WHERE username = ?", (username,))
    
    conn.commit()
    conn.close()
    
    return {"id": report_id, "status": "Reported", "tags": ai_data["tags"], "department": ai_data["department"], "priority": final_priority}

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
    cursor.execute("SELECT status, associated_report_id FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)

@app.post("/api/sessions/upload/{token}")
async def upload_session_photo(
    token: str,
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    username: str = Form("Anonymous")
):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM qr_sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Process submission
    report = await submit_report(image, latitude, longitude, username)
    cursor.execute("UPDATE qr_sessions SET status = 'uploaded', associated_report_id = ? WHERE token = ?", (report["id"], token))
    conn.commit()
    conn.close()
    return report

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
