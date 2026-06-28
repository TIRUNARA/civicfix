import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi.testclient import TestClient
import main
import database
import io

client = TestClient(main.app)

def test_file_upload():
    database.init_db()
    
    # Create a dummy image payload
    dummy_file = io.BytesIO(b"dummy image data")
    
    resp = client.post(
        "/api/reports/submit",
        files={"images": ("test_image.jpg", dummy_file, "image/jpeg")},
        data={
            "latitude": "12.9716",
            "longitude": "77.5946",
            "user_note": "Test image upload note"
        }
    )
    print("Response status code:", resp.status_code)
    print("Response json:", resp.json())
    assert resp.status_code == 200
    print("✓ Direct file upload test passed successfully!")

if __name__ == "__main__":
    test_file_upload()
