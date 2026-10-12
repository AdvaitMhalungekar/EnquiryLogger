from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ProfileType(str, Enum):
    COLLEGE_STUDENT = "College Student"
    FRESHER = "Fresher"
    WORKING_PROFESSIONAL = "Working Professional"
    CAREER_SWITCHER = "Career Switcher"


class Technology(str, Enum):
    AI_ML = "AI/ML"
    GENERATIVE_AI = "Generative AI"
    DATA_SCIENCE = "Data Science"
    AI_AGENTS = "AI Agents"
    PYTHON = "Python"
    POWER_BI = "Power BI"


ALLOWED_PROFILE_TYPES = [p.value for p in ProfileType]
ALLOWED_TECHNOLOGIES = [t.value for t in Technology]
SPREADSHEET_COLUMNS = ["Name", "Profile Type", "Interested Technologies", "Enquiry Time"]


class LLMExtractionSchema(BaseModel):
    """Pydantic schema used for LLM structured output."""
    name: Optional[str] = Field(
        default=None,
        description="Full name or first name of the speaker if explicitly mentioned. Null if not stated."
    )
    profile_type: Optional[str] = Field(
        default=None,
        description="Exactly one of: 'College Student', 'Fresher', 'Working Professional', 'Career Switcher'. Null if not clearly stated."
    )
    technologies: List[str] = Field(
        default_factory=list,
        description="List of interested technologies strictly chosen from: 'AI/ML', 'Generative AI', 'Data Science', 'AI Agents', 'Python', 'Power BI'."
    )


class ProcessedEnquiryResponse(BaseModel):
    """Response returned by POST /api/process"""
    transcript: str
    name: Optional[str] = None
    profile_type: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    enquiry_time: str
    missing_fields: List[str] = Field(default_factory=list)


class EnquirySubmission(BaseModel):
    """Payload accepted by POST /api/submit"""
    name: str = Field(..., min_length=1, description="Visitor's name")
    profile_type: str = Field(..., description="Selected profile type")
    technologies: List[str] = Field(..., min_length=1, description="List of interested technologies")
    enquiry_time: str = Field(..., description="Timestamp in YYYY-MM-DD HH:MM:SS format")

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Name cannot be empty or only whitespace")
        return clean

    @field_validator("profile_type")
    def validate_profile_type(cls, v: str) -> str:
        if v not in ALLOWED_PROFILE_TYPES:
            raise ValueError(f"Profile Type '{v}' is invalid. Allowed: {ALLOWED_PROFILE_TYPES}")
        return v

    @field_validator("technologies")
    def validate_technologies(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one technology must be selected")
        invalid = [t for t in v if t not in ALLOWED_TECHNOLOGIES]
        if invalid:
            raise ValueError(f"Invalid technology items: {invalid}. Allowed: {ALLOWED_TECHNOLOGIES}")
        # Return unique preserved order
        seen = set()
        deduped = []
        for item in v:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped


class SubmissionResponse(BaseModel):
    success: bool
    message: str
    sheet_row: Optional[int] = None
    data: Optional[dict] = None
