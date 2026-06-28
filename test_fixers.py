# Projects/civicfix/test_fixers.py
import sys
import os

# Ensure the module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import database

client = TestClient(main.app)

def test_coordinated_fixer_dispatch_and_hub():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM fixer_assignments")
    cursor.execute("DELETE FROM fixers")
    cursor.execute("DELETE FROM coordination_messages")
    
    # Pre-populate fixers
    cursor.execute("""
        INSERT INTO fixers (id, name, department, is_available)
        VALUES ('FIX-ROAD-1', 'Road Crew Alpha', 'Municipal Roads', 1)
    """)
    cursor.execute("""
        INSERT INTO fixers (id, name, department, is_available)
        VALUES ('FIX-WATER-1', 'Water Crew Beta', 'Water & Sanitation', 1)
    """)
    conn.commit()
    conn.close()

    # 1. Submit a report requiring both departments
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

    # 2. Trigger fixer dispatch directly by calling the logic or by finishing review
    # Let's finish the review via the API
    conn = database.get_db()
    cursor = conn.cursor()
    # Add reviewer assignments manually to satisfy check
    cursor.execute("INSERT INTO reviewer_assignments (report_id, reviewer_id, department, status) VALUES (?, 'REV-1', 'Municipal Roads', 'Assigned')", (report_id,))
    cursor.execute("INSERT INTO reviewer_assignments (report_id, reviewer_id, department, status) VALUES (?, 'REV-2', 'Water & Sanitation', 'Assigned')", (report_id,))
    conn.commit()
    conn.close()

    # Submit review 1
    r1 = client.post("/api/reviewer/submit-analysis", json={
        "report_id": report_id,
        "reviewer_id": "REV-1",
        "resources_logged": "Equipment A",
        "end_latitude": 12.9716,
        "end_longitude": 77.5946
    })
    assert r1.status_code == 200
    
    # Submit review 2
    r2 = client.post("/api/reviewer/submit-analysis", json={
        "report_id": report_id,
        "reviewer_id": "REV-2",
        "resources_logged": "Equipment B",
        "end_latitude": 12.9716,
        "end_longitude": 77.5946
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "Fixing"

    # 3. Verify fixer assignments
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fixer_assignments WHERE report_id = ?", (report_id,))
    fixers_assigned = cursor.fetchall()
    assert len(fixers_assigned) == 2
    
    assigned_ids = [fa["fixer_id"] for fa in fixers_assigned]
    assert "FIX-ROAD-1" in assigned_ids
    assert "FIX-WATER-1" in assigned_ids
    
    # Check reports status and is_coordinated flag
    cursor.execute("SELECT status, is_coordinated FROM reports WHERE id = ?", (report_id,))
    rep_row = cursor.fetchone()
    assert rep_row["status"] == "Fixing"
    assert rep_row["is_coordinated"] == 1
    
    # Check that fixers are marked as unavailable
    cursor.execute("SELECT id, is_available FROM fixers WHERE id IN ('FIX-ROAD-1', 'FIX-WATER-1')")
    fixers_state = cursor.fetchall()
    for f in fixers_state:
        assert f["is_available"] == 0
        
    conn.close()

    # 4. Use the inter-departmental chat hub (Segment 4)
    msg1 = client.post("/api/coordination/send-message", json={
        "report_id": report_id,
        "sender_id": "FIX-ROAD-1",
        "sender_name": "Road Crew Alpha",
        "sender_role": "Fixer",
        "message": "We have arrived at the site. Need water department to shut off main valve."
    })
    assert msg1.status_code == 200
    
    msg2 = client.post("/api/coordination/send-message", json={
        "report_id": report_id,
        "sender_id": "FIX-WATER-1",
        "sender_name": "Water Crew Beta",
        "sender_role": "Fixer",
        "message": "Valve shut off. You can start grading the road."
    })
    assert msg2.status_code == 200

    # 5. Start work
    sw_resp = client.post("/api/fixer/start-work", json={
        "report_id": report_id,
        "fixer_id": "FIX-ROAD-1"
    })
    assert sw_resp.status_code == 200
    assert sw_resp.json()["status"] == "Work in Progress"

    # Verify report status in DB
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM reports WHERE id = ?", (report_id,))
    assert cursor.fetchone()["status"] == "Work in Progress"
    
    # Verify assignment status in DB
    cursor.execute("SELECT status FROM fixer_assignments WHERE report_id = ? AND fixer_id = ?", (report_id, "FIX-ROAD-1"))
    assert cursor.fetchone()["status"] == "Work in Progress"
    conn.close()

    # Retrieve messages and verify coordination
    chat_resp = client.get(f"/api/coordination/get-messages/{report_id}")
    assert chat_resp.status_code == 200
    messages = chat_resp.json()
    assert len(messages) == 2
    assert messages[0]["sender_id"] == "FIX-ROAD-1"
    assert messages[1]["sender_id"] == "FIX-WATER-1"
    assert "valve" in messages[0]["message"]
    
    print("Segment 3/4 fixer dispatch & coordination hub verified successfully!")

if __name__ == "__main__":
    test_coordinated_fixer_dispatch_and_hub()
