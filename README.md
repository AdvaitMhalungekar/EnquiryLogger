# 🎙️ Voice Enquiry Recorder

A responsive, single-page web app and FastAPI backend that records visitor voice notes (in English or Hinglish), transcribes them, extracts structured lead details using a free Groq LLM with structured output, provides an interactive confirmation screen, and automatically appends rows to a Google Sheet.

---

## 🌟 Key Features

- **Intuitive Voice Intake:** High-contrast, mobile-friendly interface with a clear "What to Mention" guidance card.
- **Real-Time Visual Feedback:** MediaRecorder API with a live Web Audio frequency visualizer and recording timer.
- **Provider-Agnostic Transcription:** Works with Groq Whisper (`whisper-large-v3`) for lightning-fast English & Hinglish speech transcription.
- **Structured LLM Extraction:** Extracts:
  1. `Name` (Free text, never fabricated)
  2. `Profile Type` (Strictly mapped to: *College Student | Fresher | Working Professional | Career Switcher*)
  3. `Interested Technologies` (Strictly mapped to: *AI/ML | Generative AI | Data Science | AI Agents | Python | Power BI*)
  4. `Enquiry Time` (Auto-captured timestamp when recording starts in `YYYY-MM-DD HH:MM:SS` format, default `Asia/Kolkata`)
- **Interactive Review & Confirmation:**
  - Editable pre-filled fields.
  - Interactive multi-select toggle chips for technologies.
  - Missing or low-confidence fields highlighted in amber before submission.
  - Collapsible transcript accordion for transparency.
  - Re-record button to discard and speak again.
- **Robust Google Sheets Integration:**
  - Uses `gspread` with a Google Service Account.
  - Maps fields by header name, creating the header row on first run if empty.
  - Stores selected technologies comma-separated in a single cell.
- **Privacy & Security:** Audio is processed in memory and never permanently stored or logged on disk.

---

## 📁 Project Structure

```text
spreedSheetFiller/
├── backend/
│   ├── config.py                 # Pydantic Settings & environment variables
│   ├── models.py                 # Enums, Pydantic schemas (Extraction, Submission)
│   ├── main.py                   # FastAPI app, REST endpoints, static files
│   └── services/
│       ├── transcription.py     # Provider-agnostic interface & Groq Whisper
│       ├── extraction.py        # Groq LLM structured extraction & synonym normalization
│       ├── sheets.py            # gspread Google Sheets client (header-name mapping)
│       └── validation.py        # Strict code-level validation of enquiry data
├── frontend/
│   ├── index.html                # Single-page application HTML5
│   ├── style.css                 # Premium dark-theme glassmorphism design
│   └── app.js                    # MediaRecorder, Web Audio visualizer, form state
├── tests/
│   ├── test_extraction.py        # 6+ sample transcripts (complete, missing, synonyms, Hinglish)
│   ├── test_validation.py        # Strict code validation unit tests
│   └── test_api_endpoints.py     # FastAPI endpoints integration tests
├── .env.example                  # Environment variables template
├── .gitignore                    # Secrets, audio, and cache exclusion
├── README.md                     # Documentation & setup guide
└── requirements.txt              # Python dependencies
```

---

## 🛠️ Step-by-Step Setup Guide

### 1. Clone & Set Up Python Environment

```bash
cd spreedSheetFiller

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

### 2. Obtain a Free Groq API Key

1. Go to [Groq Console](https://console.groq.com/keys).
2. Sign up or log in for free.
3. Click **Create API Key** and copy your key (starts with `gsk_...`).
4. Groq provides generous free tier access for both:
   - LLM Inference: `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`
   - Audio Transcription: `whisper-large-v3`

---

### 3. Create Google Service Account & Share Google Sheet

1. **Create a Google Cloud Project:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Click **Select a project** > **New Project** and name it (e.g., `Voice-Enquiry-Intake`).
2. **Enable Required APIs:**
   - Go to **APIs & Services** > **Library**.
   - Search for **Google Sheets API** and click **Enable**.
   - Search for **Google Drive API** and click **Enable**.
3. **Create a Service Account:**
   - Go to **APIs & Services** > **Credentials**.
   - Click **Create Credentials** > **Service Account**.
   - Enter a name (e.g., `sheet-writer`) and click **Create and Continue**, then **Done**.
4. **Generate Service Account JSON Key:**
   - Click on the newly created Service Account email in the list.
   - Go to the **Keys** tab > **Add Key** > **Create new key** > Select **JSON** > **Create**.
   - A `.json` file will download to your computer.
   - Rename or copy this file into the project root as `service_account.json`.
5. **Create & Share Google Sheet:**
   - Open [Google Sheets](https://sheets.new) and create a new blank spreadsheet.
   - Note the **Spreadsheet ID** from the URL:
     `https://docs.google.com/spreadsheets/d/`**`<SHEET_ID>`**`/edit`
   - Click the green **Share** button in Google Sheets.
   - Paste your **Service Account email address** (found in your `.json` file under `client_email`, e.g. `sheet-writer@project-id.iam.gserviceaccount.com`).
   - Give it **Editor** permissions and uncheck *Notify people*, then click **Share**.

---

### 4. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_WHISPER_MODEL=whisper-large-v3
TRANSCRIPTION_PROVIDER=groq

GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=service_account.json
GOOGLE_SHEET_NAME=Sheet1

TIMEZONE=Asia/Kolkata
MAX_AUDIO_SIZE_MB=10
MAX_AUDIO_DURATION_SECONDS=120
```

---

## 🚀 Running the Web Application

Start the FastAPI server:

```bash
.venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

The single-page web app will load immediately!

---

## 🧪 Running Unit & Integration Tests

The test suite validates:
- **6 sample transcripts:**
  1. Complete enquiry
  2. Missing name
  3. Multiple technologies (3+)
  4. Synonym & variant mappings (`BTech` -> `College Student`, `ML` -> `AI/ML`, `GenAI` -> `Generative AI`, `PowerBI` -> `Power BI`)
  5. Invalid / unmentioned profile type
  6. Hinglish speech transcript
- **Code-level validation logic** (empty name, invalid enum, empty technologies, timestamp formatting)
- **FastAPI endpoints** (`/api/health`, `/api/process`, `/api/submit`)

Run the test suite with:

```bash
.venv\Scripts\pytest -v tests
```

---

## 📡 API Endpoints

### 1. `POST /api/process`
- **Request:** `multipart/form-data` with `audio` file and optional `enquiry_time` timestamp.
- **Response:**
  ```json
  {
    "transcript": "Hi, my name is Priya Sharma. I am a fresher interested in Python and Generative AI.",
    "name": "Priya Sharma",
    "profile_type": "Fresher",
    "technologies": ["Python", "Generative AI"],
    "enquiry_time": "2026-10-12 20:15:00",
    "missing_fields": []
  }
  ```

### 2. `POST /api/submit`
- **Request:**
  ```json
  {
    "name": "Priya Sharma",
    "profile_type": "Fresher",
    "technologies": ["Python", "Generative AI"],
    "enquiry_time": "2026-10-12 20:15:00"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Enquiry successfully saved to Google Sheets!",
    "sheet_row": 2,
    "data": {
      "Name": "Priya Sharma",
      "Profile Type": "Fresher",
      "Interested Technologies": "Python, Generative AI",
      "Enquiry Time": "2026-10-12 20:15:00"
    }
  }
  ```

### 3. `GET /api/health`
- Returns health status, configuration verification, and allowed enum lists.
