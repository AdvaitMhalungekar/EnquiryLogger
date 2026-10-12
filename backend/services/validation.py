import re
from typing import Dict, List, Tuple
from backend.models import (
    ALLOWED_PROFILE_TYPES,
    ALLOWED_TECHNOLOGIES,
    EnquirySubmission,
)


class ValidationError(Exception):
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


def validate_enquiry_submission(data: EnquirySubmission) -> Tuple[bool, Dict[str, str]]:
    """
    Validates the enquiry submission fields strictly in Python code:
    1. Name: non-empty string.
    2. Profile Type: exactly one of the 4 allowed values.
    3. Interested Technologies: non-empty list, all items strictly members of the 6 allowed values.
    4. Enquiry Time: non-empty timestamp string (YYYY-MM-DD HH:MM:SS format).

    Returns (is_valid, error_dict).
    """
    errors: Dict[str, str] = {}

    # Validate Name
    name = (data.name or "").strip()
    if not name:
        errors["name"] = "Name is required and cannot be empty."

    # Validate Profile Type
    if not data.profile_type or data.profile_type not in ALLOWED_PROFILE_TYPES:
        errors["profile_type"] = (
            f"Invalid profile type '{data.profile_type}'. "
            f"Must be one of: {', '.join(ALLOWED_PROFILE_TYPES)}."
        )

    # Validate Technologies
    if not data.technologies or len(data.technologies) == 0:
        errors["technologies"] = "At least one interested technology must be selected."
    else:
        invalid_techs = [t for t in data.technologies if t not in ALLOWED_TECHNOLOGIES]
        if invalid_techs:
            errors["technologies"] = (
                f"Invalid technology items: {', '.join(invalid_techs)}. "
                f"Allowed options: {', '.join(ALLOWED_TECHNOLOGIES)}."
            )

    # Validate Enquiry Time format (YYYY-MM-DD HH:MM:SS)
    time_str = (data.enquiry_time or "").strip()
    if not time_str:
        errors["enquiry_time"] = "Enquiry time is required."
    else:
        timestamp_pattern = r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$"
        if not re.match(timestamp_pattern, time_str):
            errors["enquiry_time"] = (
                f"Invalid enquiry time format '{time_str}'. Expected format: YYYY-MM-DD HH:MM:SS."
            )

    is_valid = len(errors) == 0
    return is_valid, errors
