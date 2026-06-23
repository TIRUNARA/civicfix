import gemini_service

def test_mock_fallback():
    result = gemini_service.analyze_report_image(b"mock_bytes")
    assert "department" in result
    assert "priority" in result
    print("Test passed: Gemini fallback behavior verified.")

if __name__ == "__main__":
    test_mock_fallback()
