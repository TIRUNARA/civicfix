# Projects/civicfix/test_api_filtering.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import database

client = TestClient(main.app)

def test_role_based_filtering():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM reviewer_assignments")
    cursor.execute("DELETE FROM fixer_assignments")
    
    # Insert mock reports
    cursor.execute("""
        INSERT INTO reports (id, latitude, longitude, image_path, tags, department, priority, status, created_at, updated_at)
        VALUES ('REP-ROAD-ONLY', 12.9, 77.5, '["img"]', '["Pothole"]', 'Municipal Roads', 3, 'Reviewing', '2026-06-28', '2026-06-28')
    """)
    cursor.execute("""
        INSERT INTO reports (id, latitude, longitude, image_path, tags, department, priority, status, created_at, updated_at)
        VALUES ('REP-WATER-ONLY', 12.9, 77.5, '["img"]', '["Leak"]', 'Water & Sanitation', 2, 'Reviewing', '2026-06-28', '2026-06-28')
    """)
    
    # Assign a reviewer to the road report
    cursor.execute("INSERT INTO reviewer_assignments (report_id, reviewer_id, department, status) VALUES ('REP-ROAD-ONLY', 'REV-ROAD-01', 'Municipal Roads', 'Assigned')")
    
    conn.commit()
    conn.close()

    # Test Citizen sees all
    resp = client.get("/api/reports/list?role=citizen")
    assert len(resp.json()) == 2

    # Test Reviewer gets only assigned or department reports
    resp_rev = client.get("/api/reports/list?role=reviewer&email=reviewer.roads@civicfix.gov&user_id=REV-ROAD-01")
    reports_rev = resp_rev.json()
    assert len(reports_rev) == 1
    assert reports_rev[0]["id"] == "REP-ROAD-ONLY"

    print("✓ API role-based filtering verified successfully!")

if __name__ == "__main__":
    test_role_based_filtering()
