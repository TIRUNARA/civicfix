#!/usr/bin/env python3
import os
import time
from database import get_db

def populate():
    print("Connecting to database...")
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Clear existing mock data if desired
    print("Cleaning up old database records...")
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM leaderboard")
    
    # 2. Insert Leaderboard users with emails and avatars
    users = [
        ("shiva@civicfix.org", "Shiva_The_Fixer", "https://api.dicebear.com/7.x/bottts/svg?seed=shiva", 150, 6),
        ("green@civicfix.org", "GreenCitizen", "https://api.dicebear.com/7.x/bottts/svg?seed=green", 90, 4),
        ("clean@civicfix.org", "CleanUpNow", "https://api.dicebear.com/7.x/bottts/svg?seed=clean", 45, 2)
    ]
    print("Populating leaderboard...")
    for email, username, avatar_url, points, submitted in users:
        query = "INSERT INTO leaderboard (email, username, avatar_url, civic_points, reports_submitted) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, (email, username, avatar_url, points, submitted))
        
    # 3. Insert mock reports in Bengaluru area
    reports = [
        (
            "CF-9A3B", 12.9735, 77.6075, 
            "/uploads/pothole_mock.jpg", '["Pothole", "Broken Asphalt"]', 
            "Municipal Roads", 4, 12, "Pending", "shiva@civicfix.org", "Shiva_The_Fixer"
        ),
        (
            "CF-4D1C", 12.9782, 77.6408, 
            "/uploads/fallen_tree_mock.jpg", '["Fallen Tree", "Blocked Lane"]', 
            "Parks", 3, 8, "Pending", "green@civicfix.org", "GreenCitizen"
        ),
        (
            "CF-8E2A", 12.9345, 77.6101, 
            "/uploads/garbage_mock.jpg", '["Garbage Dump", "Public Hazard"]', 
            "Solid Waste", 2, 5, "Pending", "clean@civicfix.org", "CleanUpNow"
        ),
        (
            "CF-1F7D", 12.9298, 77.5812, 
            "/uploads/streetlight_mock.jpg", '["Broken Streetlight", "Dark Alley"]', 
            "Utility Streetlighting", 1, 3, "Resolved", "shiva@civicfix.org", "Shiva_The_Fixer"
        )
    ]
    
    print("Populating reports...")
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    import base64
    import json
    for r_id, lat, lng, img, tags, dept, priority, votes, status, rep_email, rep_name in reports:
        filename = os.path.basename(img)
        filepath = os.path.join(os.path.dirname(__file__), "uploads", filename)
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                img_data = f.read()
            encoded = base64.b64encode(img_data).decode("utf-8")
            db_image_path = json.dumps([f"data:image/jpeg;base64,{encoded}"])
        else:
            db_image_path = json.dumps([img])
            
        query = """
        INSERT INTO reports (
            id, latitude, longitude, image_path, tags, 
            department, priority, votes, status, created_at, updated_at, reporter_email, reporter_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            r_id, lat, lng, db_image_path, tags, 
            dept, priority, votes, status, now_str, now_str, rep_email, rep_name
        ))
        
    conn.commit()
    conn.close()
    print("Successfully populated Neon database with live mock data!")

if __name__ == "__main__":
    populate()
