import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "allowed_profile_types" in data
    assert "allowed_technologies" in data


def test_process_audio_empty_file_rejected():
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/process",
        files={"audio": ("empty.webm", empty_file, "audio/webm")},
        data={"enquiry_time": "2026-10-12 20:00:00"}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_process_audio_success_with_mock_transcription():
    audio_content = b"RIFF....WAVEfmt ...."
    mock_transcript = "Hi, my name is Priya Sharma. I am a fresher interested in Python and Generative AI."

    with patch("backend.main.get_transcription_service") as mock_transcribe_factory:
        mock_transcribe_service = MagicMock()

        async def fake_transcribe(audio_bytes, filename):
            return mock_transcript

        mock_transcribe_service.transcribe = fake_transcribe
        mock_transcribe_factory.return_value = mock_transcribe_service

        response = client.post(
            "/api/process",
            files={"audio": ("test.webm", io.BytesIO(audio_content), "audio/webm")},
            data={"enquiry_time": "2026-10-12 20:15:00"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] == mock_transcript
        assert data["name"] == "Priya Sharma"
        assert data["profile_type"] == "Fresher"
        assert set(data["technologies"]) == {"Python", "Generative AI"}
        assert data["missing_fields"] == []
        assert data["enquiry_time"] == "2026-10-12 20:15:00"


def test_submit_enquiry_validation_failure():
    invalid_payload = {
        "name": "",
        "profile_type": "Student",  # Must be 'College Student'
        "technologies": [],
        "enquiry_time": "2026-10-12 20:00:00"
    }
    response = client.post("/api/submit", json=invalid_payload)
    assert response.status_code == 422


def test_submit_enquiry_success_with_mock_sheet():
    valid_payload = {
        "name": "Arjun Singhal",
        "profile_type": "Working Professional",
        "technologies": ["AI/ML", "AI Agents"],
        "enquiry_time": "2026-10-12 20:30:00"
    }

    with patch("backend.main.get_sheets_service") as mock_sheets_factory:
        mock_sheets = MagicMock()
        mock_sheets.append_enquiry.return_value = 5  # Row 5
        mock_sheets_factory.return_value = mock_sheets

        response = client.post("/api/submit", json=valid_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sheet_row"] == 5
        assert data["data"]["Name"] == "Arjun Singhal"
        assert data["data"]["Interested Technologies"] == "AI/ML, AI Agents"
