import pytest
from pydantic import ValidationError as PydanticValidationError
from backend.models import (
    EnquirySubmission,
    ProfileType,
    Technology,
    ALLOWED_PROFILE_TYPES,
    ALLOWED_TECHNOLOGIES,
)
from backend.services.validation import validate_enquiry_submission


class TestValidationLogic:
    """Tests code-level validation of enquiry submission before saving to Google Sheets."""

    def test_valid_submission(self):
        submission = EnquirySubmission(
            name="Aarav Sharma",
            profile_type=ProfileType.FRESHER.value,
            technologies=[Technology.PYTHON.value, Technology.GENERATIVE_AI.value],
            enquiry_time="2026-10-12 19:45:00"
        )
        is_valid, errors = validate_enquiry_submission(submission)
        assert is_valid is True
        assert errors == {}

    def test_empty_name_fails(self):
        # Empty string fails Pydantic validator
        with pytest.raises(PydanticValidationError):
            EnquirySubmission(
                name="",
                profile_type=ProfileType.COLLEGE_STUDENT.value,
                technologies=[Technology.AI_ML.value],
                enquiry_time="2026-10-12 19:45:00"
            )

        # Whitespace-only string fails validator
        with pytest.raises(PydanticValidationError):
            EnquirySubmission(
                name="   ",
                profile_type=ProfileType.COLLEGE_STUDENT.value,
                technologies=[Technology.AI_ML.value],
                enquiry_time="2026-10-12 19:45:00"
            )

    def test_invalid_profile_type_fails(self):
        with pytest.raises(PydanticValidationError) as exc_info:
            EnquirySubmission(
                name="Rohan",
                profile_type="Hobbyist Explorer",  # Not in 4 allowed
                technologies=[Technology.AI_ML.value],
                enquiry_time="2026-10-12 19:45:00"
            )
        assert "Profile Type" in str(exc_info.value)

    def test_empty_technologies_fails(self):
        with pytest.raises(PydanticValidationError):
            EnquirySubmission(
                name="Rohan",
                profile_type=ProfileType.WORKING_PROFESSIONAL.value,
                technologies=[],  # Empty list
                enquiry_time="2026-10-12 19:45:00"
            )

    def test_invalid_technology_items_fail(self):
        with pytest.raises(PydanticValidationError) as exc_info:
            EnquirySubmission(
                name="Rohan",
                profile_type=ProfileType.WORKING_PROFESSIONAL.value,
                technologies=[Technology.PYTHON.value, "Blockchain Technology"],  # Unknown item
                enquiry_time="2026-10-12 19:45:00"
            )
        assert "Blockchain Technology" in str(exc_info.value)

    def test_invalid_enquiry_time_format_detected(self):
        # Valid Pydantic object but invalid timestamp string
        submission = EnquirySubmission(
            name="Rohan",
            profile_type=ProfileType.CAREER_SWITCHER.value,
            technologies=[Technology.DATA_SCIENCE.value],
            enquiry_time="12/10/2026 7PM"  # Wrong format
        )
        is_valid, errors = validate_enquiry_submission(submission)
        assert is_valid is False
        assert "enquiry_time" in errors

    def test_technologies_deduplication(self):
        submission = EnquirySubmission(
            name="Rohan",
            profile_type=ProfileType.CAREER_SWITCHER.value,
            technologies=[Technology.PYTHON.value, Technology.PYTHON.value, Technology.AI_ML.value],
            enquiry_time="2026-10-12 20:00:00"
        )
        assert submission.technologies == [Technology.PYTHON.value, Technology.AI_ML.value]
