import gemini_service

def test_mock_fallback():
    result = gemini_service.analyze_report_image(b"mock_bytes")
    assert "tags" in result
    assert "department" in result
    assert "priority" in result
    assert "analysis" in result
    assert isinstance(result["tags"], list)
    assert result["priority"] in [1, 2, 3, 4, 5]
    print("Test passed: Gemini fallback behavior verified.")

if __name__ == "__main__":
    test_mock_fallback()
