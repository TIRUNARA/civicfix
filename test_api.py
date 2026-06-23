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

if __name__ == "__main__":
    test_endpoints()
