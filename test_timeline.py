# Projects/civicfix/test_timeline.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import database

client = TestClient(main.app)

def test_timeline_endpoint():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM report_approvals")
    cursor.execute("DELETE FROM reviewer_assignments")
    
    # Insert report
    cursor.execute("""
        INSERT INTO reports (id, latitude, longitude, image_path, tags, department, priority, status, created_at, updated_at)
        VALUES ('REP-TIMELINE-01', 12.9, 77.5, '["img"]', '["Road"]', 'Municipal Roads', 3, 'Reviewing', '2026-06-28 10:00:00', '2026-06-28 10:15:00')
    """)
    
    # Insert approvals
    cursor.execute("""
        INSERT INTO report_approvals (report_id, department, status, officer_email, approved_at)
        VALUES ('REP-TIMELINE-01', 'Municipal Roads', 'Approved', 'officer@gov.in', '2026-06-28 10:05:00')
    """)
    
    # Insert reviewer assignment
    cursor.execute("""
        INSERT INTO reviewer_assignments (report_id, reviewer_id, department, status, resources_logged, completed_at)
        VALUES ('REP-TIMELINE-01', 'REV-1', 'Municipal Roads', 'Completed', 'Asphalt bags', '2026-06-28 10:10:00')
    """)
    
    conn.commit()
    conn.close()

    resp = client.get("/api/reports/timeline/REP-TIMELINE-01")
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) >= 4  # Submission, AI Routing, Approval, Review
    assert timeline[0]["title"] == "Report Submitted"
    assert "Approved" in timeline[2]["description"]

    print("✓ Timeline aggregation endpoint verified successfully!")

if __name__ == "__main__":
    test_timeline_endpoint()
