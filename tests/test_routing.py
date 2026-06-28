# Projects/civicfix/test_routing.py
import sys
import os

# Ensure the module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import json
import database

client = TestClient(main.app)

def test_multi_department_routing_and_approval():
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports")
    cursor.execute("DELETE FROM report_approvals")
    conn.commit()
    conn.close()

    # 1. Submit a report with two departments: "Municipal Roads" and "Water & Sanitation"
    resp = client.post(
        "/api/reports/submit",
        data={
            "latitude": "12.9716",
            "longitude": "77.5946",
            "image_path": '["/uploads/pothole_mock.jpg"]',
            "tags": '["Leak", "Pothole"]',
            "department": "Municipal Roads, Water & Sanitation",
            "priority": "4",
            "description": "Broken pipe washed away asphalt"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    report_id = data["id"]
    assert "Municipal Roads" in data["department"]
    assert "Water & Sanitation" in data["department"]
    
    # 2. Check pending approvals
    app_list_resp = client.get(f"/api/reports/approvals/{report_id}")
    assert app_list_resp.status_code == 200
    approvals = app_list_resp.json()
    assert len(approvals) == 2
    
    # Status should still be Pending in reports track
    track_resp = client.get(f"/api/reports/track/{report_id}")
    assert track_resp.status_code == 200
    track_data = track_resp.json()
    assert track_data["status"] == "Pending"
    
    # 3. Approve Roads department
    app_resp = client.post(
        f"/api/reports/approve/{report_id}",
        json={"department": "Municipal Roads", "officer_email": "roads_officer@civicfix.gov"}
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "Pending"
    
    # Track status should still be Pending
    track_resp = client.get(f"/api/reports/track/{report_id}")
    assert track_resp.json()["status"] == "Pending"
    
    # 4. Approve Water department
    app_resp = client.post(
        f"/api/reports/approve/{report_id}",
        json={"department": "Water & Sanitation", "officer_email": "water_officer@civicfix.gov"}
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "Reviewing"
    
    # Track status should now be 'Reviewing'
    track_resp = client.get(f"/api/reports/track/{report_id}")
    assert track_resp.json()["status"] == "Reviewing"
    
    print("Segment 1 routing and approval flow verified successfully!")

if __name__ == "__main__":
    test_multi_department_routing_and_approval()
