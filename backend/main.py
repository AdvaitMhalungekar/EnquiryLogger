import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import pytz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models import (
    ALLOWED_PROFILE_TYPES,
    ALLOWED_TECHNOLOGIES,
    EnquirySubmission,
    ProcessedEnquiryResponse,
    SubmissionResponse,
)
from backend.services.extraction import get_extraction_service
from backend.services.sheets import get_sheets_service
from backend.services.transcription import get_transcription_service
from backend.services.validation import validate_enquiry_submission

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("voice_enquiry_recorder")

app = FastAPI(
    title="Voice Enquiry Recorder API",
    description="Record voice enquiries, extract structured fields, and append to Google Sheets",
    version="1.0.2"
)

# CORS Middleware (allows frontend integration from any origin if served separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_enquiry_time(timezone_str: str = "Asia/Kolkata") -> str:
    """Generates formatted timestamp (YYYY-MM-DD HH:MM:SS) in specified timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@app.get("/api/health")
async def health_check():
    """Health check and configuration inspection endpoint."""
    sheets_configured = bool(
        settings.GOOGLE_SHEET_ID and
        (os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_JSON_PATH) or settings.GOOGLE_SERVICE_ACCOUNT_JSON_RAW)
    )
    groq_configured = bool(settings.GROQ_API_KEY)

    return {
        "status": "healthy",
        "groq_configured": groq_configured,
        "sheets_configured": sheets_configured,
        "transcription_provider": settings.TRANSCRIPTION_PROVIDER,
        "timezone": settings.TIMEZONE,
        "allowed_profile_types": ALLOWED_PROFILE_TYPES,
        "allowed_technologies": ALLOWED_TECHNOLOGIES,
    }


@app.post("/api/process", response_model=ProcessedEnquiryResponse)
async def process_audio(
    audio: UploadFile = File(..., description="Audio file from MediaRecorder"),
    enquiry_time: Optional[str] = Form(None, description="Timestamp when recording started")
):
    """
    Accepts audio and enquiry timestamp.
    Transcribes audio (handling English and Hinglish), extracts structured fields via LLM,
    and returns transcript, extracted fields, and missing fields list.
    Audio is never stored permanently; memory is cleared immediately after processing.
    """
    logger.info(f"Received audio upload: {audio.filename}, content-type: {audio.content_type}")

    # Validate or generate enquiry timestamp
    if not enquiry_time or not enquiry_time.strip():
        enquiry_time = get_current_enquiry_time(settings.TIMEZONE)

    # Read audio bytes with size check
    max_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
    audio_bytes = await audio.read()

    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded audio file is empty. Please record your enquiry again."
        )

    if len(audio_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds maximum allowed size of {settings.MAX_AUDIO_SIZE_MB} MB."
        )

    try:
        # Step 1: Transcribe audio
        transcription_service = get_transcription_service()
        try:
            transcript = await transcription_service.transcribe(
                audio_bytes=audio_bytes,
                filename=audio.filename or "enquiry.webm"
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Audio transcription error: {str(e)}"
            )

        if not transcript or not transcript.strip():
            logger.warning("Empty transcript generated from audio")
            return ProcessedEnquiryResponse(
                transcript="",
                name=None,
                profile_type=None,
                technologies=[],
                enquiry_time=enquiry_time,
                missing_fields=["name", "profile_type", "technologies"]
            )

        # Step 2: Extract structured fields using LLM
        extraction_service = get_extraction_service()
        result = await extraction_service.extract_from_transcript(
            transcript=transcript,
            enquiry_time=enquiry_time
        )

        return result

    finally:
        # Ensure audio bytes reference is deleted from memory
        del audio_bytes


@app.post("/api/submit", response_model=SubmissionResponse)
async def submit_enquiry(enquiry: EnquirySubmission):
    """
    Accepts confirmed fields, validates them strictly in Python code,
    and appends a row to Google Sheets.
    """
    logger.info(f"Submitting enquiry for: {enquiry.name}, profile: {enquiry.profile_type}")

    # Step 1: Code-level validation
    is_valid, errors = validate_enquiry_submission(enquiry)
    if not is_valid:
        logger.warning(f"Validation failed on submission: {errors}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Submission validation failed", "errors": errors}
        )

    # Step 2: Append row to Google Sheets
    sheets_service = get_sheets_service()
    try:
        row_number = sheets_service.append_enquiry(enquiry)
        return SubmissionResponse(
            success=True,
            message="Enquiry successfully saved to Google Sheets!",
            sheet_row=row_number,
            data={
                "Name": enquiry.name,
                "Profile Type": enquiry.profile_type,
                "Interested Technologies": ", ".join(enquiry.technologies),
                "Enquiry Time": enquiry.enquiry_time,
            }
        )
    except Exception as e:
        logger.error(f"Failed to append to Google Sheets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google Sheets update failed: {str(e)}"
        )


# Mount frontend static directory if exists
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_path / "index.html"))
