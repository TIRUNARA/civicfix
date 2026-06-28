# Projects/civicfix/test_reviewers.py
import sys
import os

# Ensure the module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import database

client = TestClient(main.app)

def test_dynamic_reviewer_assignment():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM report_approvals")
    cursor.execute("DELETE FROM reviewers")
    cursor.execute("DELETE FROM reviewer_assignments")
    
    # Pre-populate test reviewers:
    # 1. Close to the report (Roads)
    cursor.execute("""
        INSERT INTO reviewers (id, name, department, latitude, longitude, is_available)
        VALUES ('REV-ROAD-1', 'Near Road Reviewer', 'Municipal Roads', 12.9710, 77.5940, 1)
    """)
    # 2. Far from the report (Roads)
    cursor.execute("""
        INSERT INTO reviewers (id, name, department, latitude, longitude, is_available)
        VALUES ('REV-ROAD-2', 'Far Road Reviewer', 'Municipal Roads', 13.0300, 77.6500, 1)
    """)
    # 3. Available (Water)
    cursor.execute("""
        INSERT INTO reviewers (id, name, department, latitude, longitude, is_available)
        VALUES ('REV-WATER-1', 'Water Reviewer', 'Water & Sanitation', 12.9720, 77.5950, 1)
    """)
    conn.commit()
    conn.close()

    # 1. Submit a report requiring both Municipal Roads and Water & Sanitation
    resp = client.post(
        "/api/reports/submit",
        data={
            "latitude": "12.9716",
            "longitude": "77.5946",
            "image_path": '["/uploads/pothole_mock.jpg"]',
            "tags": '["Leak", "Pothole"]',
            "department": "Municipal Roads, Water & Sanitation",
            "priority": "4",
            "description": "Broken pipe and washed away road"
        }
    )
    assert resp.status_code == 200
    report_id = resp.json()["id"]

    # 2. Approve both departments to trigger reviewer assignment
    resp1 = client.post(
        f"/api/reports/approve/{report_id}",
        json={"department": "Municipal Roads", "officer_email": "roads@gov.in"}
    )
    assert resp1.status_code == 200
    
    resp2 = client.post(
        f"/api/reports/approve/{report_id}",
        json={"department": "Water & Sanitation", "officer_email": "water@gov.in"}
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "Reviewing"

    # 3. Verify reviewer assignments (Nearest Roads reviewer should be REV-ROAD-1, not REV-ROAD-2)
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviewer_assignments WHERE report_id = ?", (report_id,))
    assignments = cursor.fetchall()
    
    assigned_rev_ids = [a["reviewer_id"] for a in assignments]
    assert "REV-ROAD-1" in assigned_rev_ids
    assert "REV-ROAD-2" not in assigned_rev_ids
    assert "REV-WATER-1" in assigned_rev_ids
    
    # Check that assigned reviewers are marked unavailable
    cursor.execute("SELECT id, is_available FROM reviewers WHERE id IN ('REV-ROAD-1', 'REV-WATER-1')")
    states = cursor.fetchall()
    for s in states:
        assert s["is_available"] == 0
        
    conn.close()

    # 4. Submit first reviewer analysis
    rev_resp1 = client.post(
        "/api/reviewer/submit-analysis",
        json={
            "report_id": report_id,
            "reviewer_id": "REV-ROAD-1",
            "resources_logged": "Heavy machinery needed",
            "end_latitude": 12.9715,
            "end_longitude": 77.5945
        }
    )
    assert rev_resp1.status_code == 200
    assert rev_resp1.json()["status"] == "Reviewing" # Report is still in Reviewing because REV-WATER-1 is pending

    # Verify REV-ROAD-1 is now available and location is updated
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT latitude, longitude, is_available FROM reviewers WHERE id = 'REV-ROAD-1'")
    rev1 = cursor.fetchone()
    assert rev1["is_available"] == 1
    assert abs(rev1["latitude"] - 12.9715) < 0.0001
    conn.close()

    # 5. Submit second reviewer analysis
    rev_resp2 = client.post(
        "/api/reviewer/submit-analysis",
        json={
            "report_id": report_id,
            "reviewer_id": "REV-WATER-1",
            "resources_logged": "Excavator and pipes needed",
            "end_latitude": 12.9718,
            "end_longitude": 77.5948
        }
    )
    assert rev_resp2.status_code == 200
    assert rev_resp2.json()["status"] == "Awaiting Review Approval"

    # Call the new Officer Review Approval gate to trigger fixer dispatch and status = Fixing
    approve_resp = client.post(f"/api/reports/approve-review/{report_id}")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "Fixing"

    # 6. Verify report status and fixer dispatch
    track_resp = client.get(f"/api/reports/track/{report_id}")
    assert track_resp.status_code == 200
    assert track_resp.json()["status"] == "Fixing"
    
    print("Segment 2 reviewer proximity & completion flow verified successfully!")

if __name__ == "__main__":
    test_dynamic_reviewer_assignment()
