from unittest.mock import MagicMock, patch
import gemini_service

def test_mock_fallback():
    with patch("gemini_service.client", None):
        result = gemini_service.analyze_report_image(b"mock_bytes")
        assert "tags" in result
        assert "department" in result
        assert "priority" in result
        assert "analysis" in result
        assert isinstance(result["tags"], list)
        assert result["priority"] in [1, 2, 3, 4, 5]

def test_gemini_service_with_client():
    mock_client = MagicMock()
    
    mock_response_1 = MagicMock()
    mock_response_1.text = "Visual description of a pothole."
    
    mock_response_2 = MagicMock()
    mock_response_2.text = '{"tags": ["Pothole"], "department": "Municipal Roads", "priority": 3, "analysis": "A small road pothole.", "estimated_resolution_hours": 48, "clarification_requested": false}'
    
    mock_client.models.generate_content.side_effect = [mock_response_1, mock_response_2]
    
    with patch("gemini_service.client", mock_client):
        result = gemini_service.analyze_report_image(b"mock_image_bytes")
        assert result["tags"] == ["Pothole"]
        assert result["department"] == "Municipal Roads"
        assert result["priority"] == 3
        assert result["analysis"] == "A small road pothole."
        assert mock_client.models.generate_content.call_count == 2

def test_verify_resolution_with_client():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"verified": true, "explanation": "Successfully fixed."}'
    mock_client.models.generate_content.return_value = mock_response
    
    with patch("gemini_service.client", mock_client), \
         patch("PIL.Image.open") as mock_open:
        result = gemini_service.verify_resolution(b"before", b"after")
        assert result["verified"] is True
        assert result["explanation"] == "Successfully fixed."

if __name__ == "__main__":
    test_mock_fallback()
    test_gemini_service_with_client()
    test_verify_resolution_with_client()
