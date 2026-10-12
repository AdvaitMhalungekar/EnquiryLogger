import json
import logging
import os
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials
from backend.config import settings
from backend.models import SPREADSHEET_COLUMNS, EnquirySubmission

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


class GoogleSheetsService:
    """Service to append enquiry submissions to Google Sheets using gspread."""

    def __init__(
        self,
        sheet_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        credentials_raw: Optional[str] = None,
        sheet_name: Optional[str] = None
    ):
        self.sheet_id = sheet_id or settings.GOOGLE_SHEET_ID
        self.credentials_path = credentials_path or settings.GOOGLE_SERVICE_ACCOUNT_JSON_PATH
        self.credentials_raw = credentials_raw or settings.GOOGLE_SERVICE_ACCOUNT_JSON_RAW
        self.sheet_name = sheet_name or settings.GOOGLE_SHEET_NAME
        self._client: Optional[gspread.Client] = None

    def _get_credentials(self) -> Credentials:
        if self.credentials_raw and self.credentials_raw.strip():
            try:
                info = json.loads(self.credentials_raw.strip())
                return Credentials.from_service_account_info(info, scopes=SCOPES)
            except Exception as e:
                raise ValueError(f"Invalid GOOGLE_SERVICE_ACCOUNT_JSON_RAW credentials: {e}")

        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                return Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
            except Exception as e:
                raise ValueError(f"Failed to load credentials from {self.credentials_path}: {e}")

        raise FileNotFoundError(
            f"Google Service Account credentials file not found at '{self.credentials_path}'. "
            f"Please configure GOOGLE_SERVICE_ACCOUNT_JSON_PATH or GOOGLE_SERVICE_ACCOUNT_JSON_RAW in .env."
        )

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds = self._get_credentials()
            self._client = gspread.authorize(creds)
        return self._client

    def _clean_sheet_id(self, raw_id: str) -> str:
        """Extracts the sheet key if a full Google Sheets URL was supplied."""
        raw_id = raw_id.strip()
        if "/spreadsheets/d/" in raw_id:
            parts = raw_id.split("/spreadsheets/d/")[1]
            return parts.split("/")[0]
        return raw_id

    def append_enquiry(self, enquiry: EnquirySubmission) -> int:
        """
        Appends the confirmed enquiry row to Google Sheets.
        1. Checks if sheet exists and opens it.
        2. If empty, creates header row with SPREADSHEET_COLUMNS.
        3. Maps values by header name (not static column index).
        4. Technologies are joined by comma into one cell.
        5. Returns the appended row number.
        """
        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID is not configured in .env file.")

        clean_id = self._clean_sheet_id(self.sheet_id)
        gc = self._get_client()

        try:
            spreadsheet = gc.open_by_key(clean_id)
        except Exception as e:
            logger.error(f"Failed to open Google Sheet with ID {clean_id}: {e}")
            raise RuntimeError(
                f"Could not open Google Sheet. Make sure the sheet ID is correct and "
                f"you have shared the sheet with your Service Account email address. Details: {str(e)}"
            )

        # Open worksheet
        try:
            worksheet = spreadsheet.worksheet(self.sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.sheet1

        # Check existing headers
        existing_values = worksheet.get_all_values()
        if not existing_values or len(existing_values) == 0:
            # Sheet is completely empty; initialize header row
            worksheet.append_row(SPREADSHEET_COLUMNS, value_input_option="USER_ENTERED")
            headers = SPREADSHEET_COLUMNS
        else:
            headers = existing_values[0]
            # If header row has no recognizable headers, insert standard header row
            if not any(col in headers for col in SPREADSHEET_COLUMNS):
                worksheet.insert_row(SPREADSHEET_COLUMNS, index=1, value_input_option="USER_ENTERED")
                headers = SPREADSHEET_COLUMNS

        # Map values by header name, not column position
        data_map: Dict[str, str] = {
            "Name": enquiry.name,
            "Profile Type": enquiry.profile_type,
            "Interested Technologies": ", ".join(enquiry.technologies),
            "Enquiry Time": enquiry.enquiry_time,
        }

        row_values: List[str] = []
        for header in headers:
            normalized_header = header.strip()
            # Match case-insensitively or exact
            val = ""
            for key, val_item in data_map.items():
                if normalized_header.lower() == key.lower():
                    val = val_item
                    break
            row_values.append(val)

        # Append row to Google Sheets
        worksheet.append_row(row_values, value_input_option="USER_ENTERED")

        # Row number is count of existing values + 1 (or 2 if newly created)
        total_rows = len(worksheet.get_all_values())
        logger.info(f"Successfully appended enquiry for {enquiry.name} at row {total_rows}")
        return total_rows


def get_sheets_service() -> GoogleSheetsService:
    return GoogleSheetsService()
