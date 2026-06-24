from fastapi.testclient import TestClient
import main
import io
import json

client = TestClient(main.app)

def make_tiny_image():
    from PIL import Image
    import io
    img = Image.new('RGB', (10, 10), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

def test_multistage_workflow():
    # 1. Create a QR Session
    resp = client.post("/api/sessions/create")
    assert resp.status_code == 200
    token = resp.json()["token"]
    print(f"1. QR Session Created. Token: {token}")

    # 2. Simulate Mobile Image Upload directly to /api/sessions/upload/{token}
    dummy_image = make_tiny_image()
    resp = client.post(
        f"/api/sessions/upload/{token}",
        files={"image": ("test.jpg", dummy_image, "image/jpeg")},
        data={"latitude": "12.9716", "longitude": "77.5946"}
    )
    assert resp.status_code == 200
    upload_res = resp.json()
    assert upload_res["status"] == "uploaded"
    assert "associated_report_id" in upload_res
    report_id = upload_res["associated_report_id"]
    print(f"2. Image Uploaded via Mobile. Status transitioned to uploaded. Report ID: {report_id}")

    # 3. Simulate Desktop Polling status
    resp = client.get(f"/api/sessions/status/{token}")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["status"] == "uploaded"
    assert status_data["associated_report_id"] == report_id
    print(f"3. Desktop Polling verified status = uploaded, report_id = {report_id}")

    # 4. Verify report has been created in the database and processed
    resp = client.get(f"/api/reports/track/{report_id}")
    assert resp.status_code == 200
    report_data = resp.json()
    print(f"4. Checked report state: {report_data['status']}")
    # BackgroundTasks run synchronously in FastAPI TestClient, so it should be fully processed ('Reported')
    assert report_data["status"] == "Reported"
    print(f"Integration test complete!")

def test_multistage_workflow_with_user():
    # 1. Create a QR Session with user info
    resp = client.post(
        "/api/sessions/create",
        json={
            "reporter_email": "test-user@civicfix.org",
            "reporter_name": "Test User",
            "reporter_avatar": "https://avatar-url.com/img"
        }
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    print(f"1. QR Session with User Created. Token: {token}")

    # 2. Simulate Mobile Image Upload
    dummy_image = make_tiny_image()
    resp = client.post(
        f"/api/sessions/upload/{token}",
        files={"image": ("test.jpg", dummy_image, "image/jpeg")},
        data={"latitude": "12.9716", "longitude": "77.5946"}
    )
    assert resp.status_code == 200
    upload_res = resp.json()
    report_id = upload_res["associated_report_id"]

    # 3. Check report metadata
    resp = client.get(f"/api/reports/track/{report_id}")
    assert resp.status_code == 200
    report_data = resp.json()
    assert report_data["reporter_email"] == "test-user@civicfix.org"
    assert report_data["reporter_name"] == "Test User"
    print(f"Verified report belongs to: {report_data['reporter_email']} ({report_data['reporter_name']})")

if __name__ == "__main__":
    test_multistage_workflow()
    test_multistage_workflow_with_user()
