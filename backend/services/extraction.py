import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from backend.config import settings
from backend.models import (
    ALLOWED_PROFILE_TYPES,
    ALLOWED_TECHNOLOGIES,
    LLMExtractionSchema,
    ProcessedEnquiryResponse,
    ProfileType,
    Technology,
)

logger = logging.getLogger(__name__)

# Canonical Synonym Mappings
PROFILE_SYNONYM_MAP: Dict[str, str] = {
    # College Student
    "student": ProfileType.COLLEGE_STUDENT.value,
    "college student": ProfileType.COLLEGE_STUDENT.value,
    "college": ProfileType.COLLEGE_STUDENT.value,
    "btech": ProfileType.COLLEGE_STUDENT.value,
    "b.tech": ProfileType.COLLEGE_STUDENT.value,
    "bca": ProfileType.COLLEGE_STUDENT.value,
    "mca": ProfileType.COLLEGE_STUDENT.value,
    "mtech": ProfileType.COLLEGE_STUDENT.value,
    "pursuing degree": ProfileType.COLLEGE_STUDENT.value,
    "pursuing graduation": ProfileType.COLLEGE_STUDENT.value,
    "pursuing btech": ProfileType.COLLEGE_STUDENT.value,
    "undergraduate": ProfileType.COLLEGE_STUDENT.value,
    "in college": ProfileType.COLLEGE_STUDENT.value,
    "studying": ProfileType.COLLEGE_STUDENT.value,

    # Fresher
    "fresher": ProfileType.FRESHER.value,
    "recent graduate": ProfileType.FRESHER.value,
    "just graduated": ProfileType.FRESHER.value,
    "new graduate": ProfileType.FRESHER.value,
    "passed out": ProfileType.FRESHER.value,
    "passout": ProfileType.FRESHER.value,
    "fresh graduate": ProfileType.FRESHER.value,

    # Working Professional
    "working professional": ProfileType.WORKING_PROFESSIONAL.value,
    "employed": ProfileType.WORKING_PROFESSIONAL.value,
    "job": ProfileType.WORKING_PROFESSIONAL.value,
    "it professional": ProfileType.WORKING_PROFESSIONAL.value,
    "software engineer": ProfileType.WORKING_PROFESSIONAL.value,
    "software developer": ProfileType.WORKING_PROFESSIONAL.value,
    "working": ProfileType.WORKING_PROFESSIONAL.value,
    "employed in": ProfileType.WORKING_PROFESSIONAL.value,
    "corporate": ProfileType.WORKING_PROFESSIONAL.value,

    # Career Switcher
    "career switcher": ProfileType.CAREER_SWITCHER.value,
    "changing careers": ProfileType.CAREER_SWITCHER.value,
    "switching from": ProfileType.CAREER_SWITCHER.value,
    "career switch": ProfileType.CAREER_SWITCHER.value,
    "career change": ProfileType.CAREER_SWITCHER.value,
    "switching domain": ProfileType.CAREER_SWITCHER.value,
    "transitioning": ProfileType.CAREER_SWITCHER.value,
}

TECHNOLOGY_SYNONYM_MAP: Dict[str, str] = {
    # AI/ML
    "ai/ml": Technology.AI_ML.value,
    "ai & ml": Technology.AI_ML.value,
    "ai and ml": Technology.AI_ML.value,
    "aiml": Technology.AI_ML.value,
    "machine learning": Technology.AI_ML.value,
    "ml": Technology.AI_ML.value,
    "artificial intelligence": Technology.AI_ML.value,
    "ai": Technology.AI_ML.value,

    # Generative AI
    "generative ai": Technology.GENERATIVE_AI.value,
    "genai": Technology.GENERATIVE_AI.value,
    "gen ai": Technology.GENERATIVE_AI.value,
    "generative artificial intelligence": Technology.GENERATIVE_AI.value,
    "llm": Technology.GENERATIVE_AI.value,
    "llms": Technology.GENERATIVE_AI.value,
    "large language models": Technology.GENERATIVE_AI.value,

    # Data Science
    "data science": Technology.DATA_SCIENCE.value,
    "datascience": Technology.DATA_SCIENCE.value,
    "data scientist": Technology.DATA_SCIENCE.value,
    "ds": Technology.DATA_SCIENCE.value,

    # AI Agents
    "ai agents": Technology.AI_AGENTS.value,
    "agents": Technology.AI_AGENTS.value,
    "agentic ai": Technology.AI_AGENTS.value,
    "agentic": Technology.AI_AGENTS.value,
    "ai agent": Technology.AI_AGENTS.value,
    "agent": Technology.AI_AGENTS.value,
    "agentic workflows": Technology.AI_AGENTS.value,

    # Python
    "python": Technology.PYTHON.value,
    "python programming": Technology.PYTHON.value,
    "python coding": Technology.PYTHON.value,

    # Power BI
    "power bi": Technology.POWER_BI.value,
    "powerbi": Technology.POWER_BI.value,
    "power bi desktop": Technology.POWER_BI.value,
    "powerbi desktop": Technology.POWER_BI.value,
}

EXTRACTION_SYSTEM_PROMPT = """You are an accurate enquiry detail extractor for an educational institute.
The speaker is an admissions counselor or marketing executive summarizing a phone call enquiry they just received from a prospective student or client (spoken in third person or reported speech, in English or Hinglish).

Common speaker phrasing:
- "The student name is Rahul Sharma, he is a college student pursuing BTech, interested in Python and Generative AI."
- "Client name is Priya, currently working as a software developer, wants to learn AI Agents and Data Science."
- "Got an enquiry from Amit Verma, fresher, asked about Power BI."
- "Candidate is Vikram, career switcher from sales, interested in Data Science and Python."
- "Call aaya tha Neha se, working professional hai, AI/ML seekhna chahti hai."
- "Student name Rohit, fresher, interested in Generative AI."

Extract the PROSPECTIVE STUDENT / CLIENT details (NOT the admissions counselor):
1. "name": The student/client/caller's name (string). If not mentioned, return null. Never guess or fabricate names!
2. "profile_type": Exactly one of:
   - "College Student"
   - "Fresher"
   - "Working Professional"
   - "Career Switcher"
   Synonym mapping rules:
   - "student", "college student", "college", "BTech", "bca", "mca", "pursuing degree", "studying", "undergrad" -> "College Student"
   - "fresher", "recent graduate", "just graduated", "passout", "new graduate", "fresh graduate" -> "Fresher"
   - "employed", "job", "IT professional", "software engineer", "developer", "working", "working professional" -> "Working Professional"
   - "changing careers", "switching from X", "career switch", "career transition" -> "Career Switcher"
   If the prospect's profile is not clearly stated, return null. Never guess!
3. "technologies": A JSON array of interested technologies, containing ONLY valid values from this exact list:
   - "AI/ML" (variants: "machine learning", "ML", "AI/ML", "artificial intelligence")
   - "Generative AI" (variants: "GenAI", "LLMs", "Generative AI")
   - "Data Science" (variants: "data science", "data scientist")
   - "AI Agents" (variants: "agents", "agentic AI", "AI agents")
   - "Python" (variants: "Python", "Python programming")
   - "Power BI" (variants: "PowerBI", "Power BI", "power bi desktop")
   If no technologies are mentioned, return [].

CRITICAL RULES:
- Output MUST be valid JSON only.
- Use null for anything not clearly stated. Never guess.
- Do NOT output fields that were not mentioned.
- Accurately process English and Hinglish phone enquiry notes.

JSON Schema:
{
  "name": string or null,
  "profile_type": string or null,
  "technologies": ["string", ...]
}
"""


def normalize_profile_type(raw_val: Optional[str]) -> Optional[str]:
    """Deterministically normalizes and maps profile type synonyms."""
    if not raw_val:
        return None
    val = raw_val.strip()
    if val in ALLOWED_PROFILE_TYPES:
        return val

    lower = val.lower()
    # Check direct dictionary lookup
    if lower in PROFILE_SYNONYM_MAP:
        return PROFILE_SYNONYM_MAP[lower]

    # Substring search in synonym keys
    for pattern, canonical in PROFILE_SYNONYM_MAP.items():
        if pattern in lower:
            return canonical

    return None


def normalize_technologies(raw_list: Optional[List[str]]) -> List[str]:
    """Deterministically normalizes and maps technology variants, eliminating duplicates."""
    if not raw_list:
        return []

    normalized_set = []
    for item in raw_list:
        if not item or not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned in ALLOWED_TECHNOLOGIES:
            if cleaned not in normalized_set:
                normalized_set.append(cleaned)
            continue

        lower = cleaned.lower()
        matched = False
        # Direct lookup
        if lower in TECHNOLOGY_SYNONYM_MAP:
            canonical = TECHNOLOGY_SYNONYM_MAP[lower]
            if canonical not in normalized_set:
                normalized_set.append(canonical)
            matched = True
        else:
            # Check substrings
            for pattern, canonical in TECHNOLOGY_SYNONYM_MAP.items():
                if pattern in lower:
                    if canonical not in normalized_set:
                        normalized_set.append(canonical)
                    matched = True
                    break

    # Preserve canonical order
    return [t for t in ALLOWED_TECHNOLOGIES if t in normalized_set]


def compute_missing_fields(
    name: Optional[str],
    profile_type: Optional[str],
    technologies: List[str]
) -> List[str]:
    """Calculates missing fields according to business rules."""
    missing = []
    if not name or not name.strip():
        missing.append("name")
    if not profile_type or profile_type not in ALLOWED_PROFILE_TYPES:
        missing.append("profile_type")
    if not technologies or len(technologies) == 0:
        missing.append("technologies")
    return missing


class ExtractionService:
    """Service to extract structured enquiry fields from transcripts using Groq LLM."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL

    async def extract_from_transcript(
        self,
        transcript: str,
        enquiry_time: str
    ) -> ProcessedEnquiryResponse:
        """
        Calls Groq LLM with structured output, normalizes the response,
        identifies missing fields, and returns a ProcessedEnquiryResponse.
        """
        if not transcript or not transcript.strip():
            return ProcessedEnquiryResponse(
                transcript="",
                name=None,
                profile_type=None,
                technologies=[],
                enquiry_time=enquiry_time,
                missing_fields=["name", "profile_type", "technologies"]
            )

        # Fallback to local rule-based extractor if no API key is provided
        if not self.api_key:
            logger.warning("GROQ_API_KEY not configured. Falling back to rule-based extractor.")
            return self.rule_based_extract(transcript, enquiry_time)

        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            user_prompt = f"Audio transcript to extract:\n\"\"\"{transcript}\"\"\""

            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            raw_content = completion.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            raw_name = parsed.get("name")
            if isinstance(raw_name, str):
                raw_name = raw_name.strip()
                if raw_name.lower() in ("null", "none", "unknown", "n/a", ""):
                    raw_name = None

            raw_profile = parsed.get("profile_type")
            raw_techs = parsed.get("technologies") or []

            # Normalize using deterministic synonym mappings
            normalized_profile = normalize_profile_type(raw_profile)
            normalized_techs = normalize_technologies(raw_techs)

            # Extra rule: if LLM didn't catch synonyms from transcript, run fallback pattern match
            if not normalized_profile:
                normalized_profile = self._pattern_match_profile(transcript)
            if not normalized_techs:
                normalized_techs = self._pattern_match_technologies(transcript)

            missing_fields = compute_missing_fields(
                raw_name,
                normalized_profile,
                normalized_techs
            )

            return ProcessedEnquiryResponse(
                transcript=transcript,
                name=raw_name,
                profile_type=normalized_profile,
                technologies=normalized_techs,
                enquiry_time=enquiry_time,
                missing_fields=missing_fields
            )
        except Exception as e:
            logger.error(f"Error during LLM extraction: {e}. Using rule-based fallback.")
            return self.rule_based_extract(transcript, enquiry_time)

    def _pattern_match_profile(self, text: str) -> Optional[str]:
        lower = text.lower()
        # Direct word matches
        if re.search(r"\b(student|b\.?tech|bca|mca|m\.?tech|college|pursuing degree|undergrad)\b", lower):
            return ProfileType.COLLEGE_STUDENT.value
        if re.search(r"\b(fresher|recent graduate|just graduated|passed out|passout|fresh graduate)\b", lower):
            return ProfileType.FRESHER.value
        if re.search(r"\b(working|employed|job|it professional|software engineer|developer|corporate)\b", lower):
            return ProfileType.WORKING_PROFESSIONAL.value
        if re.search(r"\b(career switcher|career switch|career change|switcher|switching|transition|change domain)\b", lower):
            return ProfileType.CAREER_SWITCHER.value
        return None

    def _pattern_match_technologies(self, text: str) -> List[str]:
        lower = text.lower()
        found = []
        if re.search(r"\b(ai/ml|machine learning|\bml\b|artificial intelligence)\b", lower):
            found.append(Technology.AI_ML.value)
        if re.search(r"\b(generative ai|genai|gen ai|llm|llms)\b", lower):
            found.append(Technology.GENERATIVE_AI.value)
        if re.search(r"\b(data science|datascience|data scientist)\b", lower):
            found.append(Technology.DATA_SCIENCE.value)
        if re.search(r"\b(ai agents|agentic|agents|agentic ai)\b", lower):
            found.append(Technology.AI_AGENTS.value)
        if re.search(r"\b(python|python programming)\b", lower):
            found.append(Technology.PYTHON.value)
        if re.search(r"\b(power bi|powerbi)\b", lower):
            found.append(Technology.POWER_BI.value)
        return [t for t in ALLOWED_TECHNOLOGIES if t in found]

    def rule_based_extract(self, transcript: str, enquiry_time: str) -> ProcessedEnquiryResponse:
        """Deterministic extractor used for unit tests or fallback when API key is missing."""
        lower = transcript.lower()

        # Extract prospect name using third-person and first-person patterns
        name: Optional[str] = None
        name_patterns = [
            # Third-person call notes phrasing (Counselor speaking about prospect)
            r"(?:the\s+)?(?:client(?:\s+name)?|student(?:\s+name)?|candidate(?:\s+name)?|caller(?:\s+name)?|lead(?:\s+name)?|prospect(?:\s+name)?)\s+(?:is|was|named)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
            r"(?:got\s+an\s+enquiry\s+from|enquiry\s+from|call\s+from|call\s+with|spoke\s+to|spoke\s+with|talked\s+to|talked\s+with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
            r"(?:call\s+aaya\s+tha|enquiry\s+aayi\s+thi)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:se|ka|ki)",
            r"(?:name\s+is|naam\s+hai)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
            # First-person phrasing fallback
            r"(?:my\s+name\s+is|i\s+am|i'm|this\s+is|mera\s+naam\s+hai|mera\s+naam)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
            r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+here"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # filter common stop words
                if extracted.lower() not in ("a", "an", "the", "interested", "looking", "here", "call", "enquiry", "today"):
                    name = extracted.title()
                    break

        profile_type = self._pattern_match_profile(transcript)
        technologies = self._pattern_match_technologies(transcript)
        missing_fields = compute_missing_fields(name, profile_type, technologies)

        return ProcessedEnquiryResponse(
            transcript=transcript,
            name=name,
            profile_type=profile_type,
            technologies=technologies,
            enquiry_time=enquiry_time,
            missing_fields=missing_fields
        )


def get_extraction_service() -> ExtractionService:
    return ExtractionService()
