from fastapi.testclient import TestClient
import main
import io
import json

client = TestClient(main.app)

def test_multistage_workflow():
    # 1. Create a QR Session
    resp = client.post("/api/sessions/create")
    assert resp.status_code == 200
    token = resp.json()["token"]
    print(f"1. QR Session Created. Token: {token}")

    # 2. Simulate Mobile Image Upload to /api/sessions/upload/{token}
    dummy_image = io.BytesIO(b"fake_jpeg_content")
    resp = client.post(
        f"/api/sessions/upload/{token}",
        files={"image": ("test.jpg", dummy_image, "image/jpeg")},
        data={"latitude": "12.9716", "longitude": "77.5946"}
    )
    assert resp.status_code == 200
    upload_res = resp.json()
    assert upload_res["status"] == "draft"
    assert "draft_data" in upload_res
    draft_data = upload_res["draft_data"]
    print(f"2. Image Uploaded via Mobile. Status changed to draft.")
    print(f"Draft data received: {json.dumps(draft_data, indent=2)}")

    # 3. Simulate Desktop Polling status
    resp = client.get(f"/api/sessions/status/{token}")
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["status"] == "draft"
    assert status_data["draft_data"] is not None
    print(f"3. Desktop Polling verified status = draft.")

    # 4. Simulate Desktop Audited Submission (auditing AI suggestions)
    # The desktop edits some tags and submits
    edited_tags = ["Pothole", "Dangerous", "Road Hazard"]
    resp = client.post(
        "/api/reports/submit",
        data={
            "image_path": draft_data["image_path"],
            "latitude": "12.9716",
            "longitude": "77.5946",
            "tags": json.dumps(edited_tags),
            "department": "Roads & Traffic",
            "priority": "5",
            "description": "A very large pothole that needs immediate attention.",
            "reporter_email": "shiva@civicfix.org",
            "reporter_name": "Shiva",
            "reporter_avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=shiva",
            "token": token
        }
    )
    assert resp.status_code == 200
    submit_res = resp.json()
    assert "id" in submit_res
    report_id = submit_res["id"]
    print(f"4. Final audited report submitted. Report ID: {report_id}")

    # 5. Check session status has transitioned to 'uploaded'
    resp = client.get(f"/api/sessions/status/{token}")
    assert resp.status_code == 200
    final_status_data = resp.json()
    assert final_status_data["status"] == "uploaded"
    print(f"5. Session status updated to uploaded. Integration test complete!")

if __name__ == "__main__":
    test_multistage_workflow()
