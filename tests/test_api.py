from fastapi.testclient import TestClient
from unittest.mock import patch
import main
import os

client = TestClient(main.app)

def test_endpoints():
    # Health check endpoint
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Test session creation
    resp = client.post("/api/sessions/create")
    assert resp.status_code == 200
    token = resp.json()["token"]
    
    # Test session status endpoint
    resp = client.get(f"/api/sessions/status/{token}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    print("Test passed: FastAPI endpoints behaving correctly.")

def test_path_traversal_protection():
    # Attempting path traversal on submit
    resp = client.post(
        "/api/reports/submit",
        data={
            "latitude": "12.9716",
            "longitude": "77.5946",
            "image_path": "../../../../etc/passwd",
            "tags": '["Pothole"]',
            "department": "Roads & Traffic",
            "priority": 3,
            "description": "Path traversal attempt"
        }
    )
    assert resp.status_code in [400, 404]
    print("Test passed: Path traversal protection on report submit verified.")

def test_clarification_flow():
    # Mock verify_image_quality to fail quality check
    with patch("gemini_service.verify_image_quality", return_value={"valid": False, "issues": ["blurry"]}):
        # Submit report asynchronously (without tags/dept/priority)
        resp = client.post(
            "/api/reports/submit",
            data={
                "latitude": "12.9716",
                "longitude": "77.5946",
                "image_path": "data:image/jpeg;base64,dGVzdA==" # "test" encoded in base64
            }
        )
        assert resp.status_code == 200
        report_id = resp.json()["id"]
        
        # TestClient runs background tasks synchronously, so the DB should already be updated
        resp_track = client.get(f"/api/reports/track/{report_id}")
        assert resp_track.status_code == 200
        report_data = resp_track.json()
        assert report_data["status"] == "Clarification Needed"
        assert "is blurry" in report_data["description"]
        print("Test passed: Clarification Flow successfully triggered 'Clarification Needed' state.")

if __name__ == "__main__":
    test_endpoints()
    test_path_traversal_protection()
    test_clarification_flow()
