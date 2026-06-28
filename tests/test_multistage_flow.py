from fastapi.testclient import TestClient
import main
import io
import json
import time

import gemini_service
gemini_service.client = None

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
    assert upload_res["status"] == "processing"
    print(f"2. Image Uploaded via Mobile. Status transitioned to processing.")

    # 3. Simulate Desktop Polling status until 'draft'
    draft_data = None
    for _ in range(20):
        resp = client.get(f"/api/sessions/status/{token}")
        assert resp.status_code == 200
        status_data = resp.json()
        if status_data["status"] == "draft":
            draft_data = status_data["draft_data"]
            break
        time.sleep(0.2)

    assert draft_data is not None
    print(f"3. Desktop Polling verified status = draft. Draft data: {draft_data}")

    # 4. Confirm/Submit Draft from Desktop
    resp = client.post(
        "/api/reports/submit",
        data={
            "token": token,
            "latitude": draft_data["latitude"],
            "longitude": draft_data["longitude"],
            "image_path": draft_data["image_path"],
            "tags": json.dumps(draft_data["tags"]),
            "department": draft_data["department"],
            "priority": draft_data["priority"],
            "description": draft_data["analysis"]
        }
    )
    assert resp.status_code == 200
    submit_res = resp.json()
    assert submit_res["status"] == "Pending"
    report_id = submit_res["id"]
    print(f"4. Confirmed draft. Created report ID: {report_id}")

    # 5. Verify session status is updated to uploaded and linked to report_id
    resp = client.get(f"/api/sessions/status/{token}")
    assert resp.status_code == 200
    sess_status = resp.json()
    assert sess_status["status"] == "uploaded"
    assert sess_status["associated_report_id"] == report_id

    # 6. Verify report status is Pending in the database
    resp = client.get(f"/api/reports/track/{report_id}")
    assert resp.status_code == 200
    report_data = resp.json()
    assert report_data["status"] == "Pending"
    print(f"5. Checked report state: {report_data['status']}")
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
    assert upload_res["status"] == "processing"

    # 3. Poll until draft
    draft_data = None
    for _ in range(20):
        resp = client.get(f"/api/sessions/status/{token}")
        assert resp.status_code == 200
        status_data = resp.json()
        if status_data["status"] == "draft":
            draft_data = status_data["draft_data"]
            break
        time.sleep(0.2)

    assert draft_data is not None
    assert draft_data["reporter_email"] == "test-user@civicfix.org"
    assert draft_data["reporter_name"] == "Test User"

    # 4. Confirm/Submit Draft
    resp = client.post(
        "/api/reports/submit",
        data={
            "token": token,
            "latitude": draft_data["latitude"],
            "longitude": draft_data["longitude"],
            "image_path": draft_data["image_path"],
            "tags": json.dumps(draft_data["tags"]),
            "department": draft_data["department"],
            "priority": draft_data["priority"],
            "description": draft_data["analysis"],
            "reporter_email": draft_data["reporter_email"],
            "reporter_name": draft_data["reporter_name"],
            "reporter_avatar": draft_data["reporter_avatar"]
        }
    )
    assert resp.status_code == 200
    submit_res = resp.json()
    assert submit_res["status"] == "Pending"
    report_id = submit_res["id"]

    # 5. Check report metadata
    resp = client.get(f"/api/reports/track/{report_id}")
    assert resp.status_code == 200
    report_data = resp.json()
    assert report_data["reporter_email"] == "test-user@civicfix.org"
    assert report_data["reporter_name"] == "Test User"
    print(f"Verified report belongs to: {report_data['reporter_email']} ({report_data['reporter_name']})")

if __name__ == "__main__":
    test_multistage_workflow()
    test_multistage_workflow_with_user()
