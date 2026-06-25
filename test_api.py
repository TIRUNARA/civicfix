from fastapi.testclient import TestClient
import main
import os

client = TestClient(main.app)

def test_endpoints():
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

if __name__ == "__main__":
    test_endpoints()
    test_path_traversal_protection()
