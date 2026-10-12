import json
import pytest
from unittest.mock import MagicMock, patch
from backend.services.extraction import (
    ExtractionService,
    normalize_profile_type,
    normalize_technologies,
    compute_missing_fields,
)
from backend.models import ProfileType, Technology


# 6 Sample Transcripts as required by specifications
TRANSCRIPTS = {
    # 1. Complete transcript
    "complete": "Hi, my name is Priya Sharma. I am a fresher and I am interested in Python and Generative AI.",

    # 2. Missing name transcript
    "missing_name": "Hello, I am a working professional with 3 years in IT, looking to learn AI/ML and AI Agents.",

    # 3. Multiple technologies transcript (3+ technologies)
    "multiple_technologies": "My name is Amit Verma. I am a college student and I want to learn Python, Data Science, and Power BI.",

    # 4. Using synonyms ("pursuing BTech" -> College Student, "ML" -> AI/ML, "GenAI" -> Generative AI, "PowerBI" -> Power BI)
    "synonyms": "Hey, I am Rohan Gupta. Currently pursuing BTech degree and I want to master ML, GenAI and PowerBI.",

    # 5. Invalid / unmentioned profile type (missing profile type)
    "invalid_profile": "Hi there, my name is Neha Gupta. I want to learn Data Science, but I am just exploring courses right now.",

    # 6. Hinglish mix transcript (Hindi-English mix)
    "hinglish": "Mera naam Rajesh Kumar hai, main IT me job kar raha hoon aur mujhe Generative AI aur AI Agents sikhna hai.",

    # 7. Career Switcher transcript
    "career_switcher": "Hello, I am Suresh Patel. I am switching from finance to data analytics, interested in Data Science and Power BI.",

    # 8. Third-person marketing counselor notes (Call summaries)
    "counselor_student": "The student name is Rahul Sharma, he is a college student pursuing BTech, interested in Python and Generative AI.",
    "counselor_client": "Client name is Priya Verma, working professional in software, looking for AI Agents and Data Science.",
    "counselor_enquiry_from": "Got an enquiry from Amit Patel, fresher, interested in Power BI.",
    "counselor_candidate": "Candidate is Vikram Malhotra, career switcher from sales, interested in Data Science and Python."
}


class TestSynonymAndNormalizationLogic:
    """Tests the canonical normalization and synonym mapping rules."""

    def test_profile_synonym_mappings(self):
        # College Student synonyms
        assert normalize_profile_type("student") == ProfileType.COLLEGE_STUDENT.value
        assert normalize_profile_type("BTech") == ProfileType.COLLEGE_STUDENT.value
        assert normalize_profile_type("pursuing degree") == ProfileType.COLLEGE_STUDENT.value
        assert normalize_profile_type("college student") == ProfileType.COLLEGE_STUDENT.value

        # Fresher synonyms
        assert normalize_profile_type("fresher") == ProfileType.FRESHER.value
        assert normalize_profile_type("recent graduate") == ProfileType.FRESHER.value
        assert normalize_profile_type("just graduated") == ProfileType.FRESHER.value

        # Working Professional synonyms
        assert normalize_profile_type("working professional") == ProfileType.WORKING_PROFESSIONAL.value
        assert normalize_profile_type("employed") == ProfileType.WORKING_PROFESSIONAL.value
        assert normalize_profile_type("job") == ProfileType.WORKING_PROFESSIONAL.value
        assert normalize_profile_type("IT professional") == ProfileType.WORKING_PROFESSIONAL.value

        # Career Switcher synonyms
        assert normalize_profile_type("career switcher") == ProfileType.CAREER_SWITCHER.value
        assert normalize_profile_type("changing careers") == ProfileType.CAREER_SWITCHER.value
        assert normalize_profile_type("switching from finance") == ProfileType.CAREER_SWITCHER.value

        # Unknown / Invalid profile returns None
        assert normalize_profile_type("just exploring") is None
        assert normalize_profile_type("hobbyist") is None
        assert normalize_profile_type(None) is None
        assert normalize_profile_type("") is None

    def test_technology_variant_mappings(self):
        # AI/ML variants
        assert normalize_technologies(["machine learning", "ML"]) == [Technology.AI_ML.value]
        # Generative AI variants
        assert normalize_technologies(["GenAI", "LLMs"]) == [Technology.GENERATIVE_AI.value]
        # AI Agents variants
        assert normalize_technologies(["agents", "agentic AI"]) == [Technology.AI_AGENTS.value]
        # Power BI variants
        assert normalize_technologies(["PowerBI", "power bi desktop"]) == [Technology.POWER_BI.value]
        # Combined deduplication and order preservation
        raw_list = ["Python", "python", "machine learning", "PowerBI", "Generative AI"]
        normalized = normalize_technologies(raw_list)
        assert normalized == [Technology.AI_ML.value, Technology.GENERATIVE_AI.value, Technology.PYTHON.value, Technology.POWER_BI.value]

    def test_compute_missing_fields(self):
        # All present
        assert compute_missing_fields("Rahul", "Fresher", ["Python"]) == []
        # Missing name
        assert compute_missing_fields(None, "Fresher", ["Python"]) == ["name"]
        # Missing profile
        assert compute_missing_fields("Rahul", None, ["Python"]) == ["profile_type"]
        # Missing technologies
        assert compute_missing_fields("Rahul", "Fresher", []) == ["technologies"]
        # All missing
        assert compute_missing_fields(None, None, []) == ["name", "profile_type", "technologies"]


class TestRuleBasedExtraction:
    """Verifies the 6 key transcripts on the deterministic extraction engine."""

    def setup_method(self):
        self.extractor = ExtractionService()
        self.timestamp = "2026-10-12 20:00:00"

    def test_transcript_1_complete(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["complete"], self.timestamp)
        assert res.name == "Priya Sharma"
        assert res.profile_type == ProfileType.FRESHER.value
        assert set(res.technologies) == {Technology.PYTHON.value, Technology.GENERATIVE_AI.value}
        assert res.missing_fields == []
        assert res.enquiry_time == self.timestamp

    def test_transcript_2_missing_name(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["missing_name"], self.timestamp)
        assert res.name is None
        assert res.profile_type == ProfileType.WORKING_PROFESSIONAL.value
        assert set(res.technologies) == {Technology.AI_ML.value, Technology.AI_AGENTS.value}
        assert "name" in res.missing_fields
        assert "profile_type" not in res.missing_fields
        assert "technologies" not in res.missing_fields

    def test_transcript_3_multiple_technologies(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["multiple_technologies"], self.timestamp)
        assert res.name == "Amit Verma"
        assert res.profile_type == ProfileType.COLLEGE_STUDENT.value
        assert set(res.technologies) == {Technology.PYTHON.value, Technology.DATA_SCIENCE.value, Technology.POWER_BI.value}
        assert res.missing_fields == []

    def test_transcript_4_synonyms(self):
        # BTech -> College Student; ML -> AI/ML; GenAI -> Generative AI; PowerBI -> Power BI
        res = self.extractor.rule_based_extract(TRANSCRIPTS["synonyms"], self.timestamp)
        assert res.name == "Rohan Gupta"
        assert res.profile_type == ProfileType.COLLEGE_STUDENT.value
        assert set(res.technologies) == {Technology.AI_ML.value, Technology.GENERATIVE_AI.value, Technology.POWER_BI.value}
        assert res.missing_fields == []

    def test_transcript_5_invalid_profile(self):
        # Neha Gupta; exploring -> no profile stated
        res = self.extractor.rule_based_extract(TRANSCRIPTS["invalid_profile"], self.timestamp)
        assert res.name == "Neha Gupta"
        assert res.profile_type is None
        assert set(res.technologies) == {Technology.DATA_SCIENCE.value}
        assert "profile_type" in res.missing_fields

    def test_transcript_6_hinglish(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["hinglish"], self.timestamp)
        assert res.name == "Rajesh Kumar"
        assert res.profile_type == ProfileType.WORKING_PROFESSIONAL.value
        assert set(res.technologies) == {Technology.GENERATIVE_AI.value, Technology.AI_AGENTS.value}
        assert res.missing_fields == []

    def test_counselor_note_student(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["counselor_student"], self.timestamp)
        assert res.name == "Rahul Sharma"
        assert res.profile_type == ProfileType.COLLEGE_STUDENT.value
        assert set(res.technologies) == {Technology.PYTHON.value, Technology.GENERATIVE_AI.value}
        assert res.missing_fields == []

    def test_counselor_note_client(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["counselor_client"], self.timestamp)
        assert res.name == "Priya Verma"
        assert res.profile_type == ProfileType.WORKING_PROFESSIONAL.value
        assert set(res.technologies) == {Technology.AI_AGENTS.value, Technology.DATA_SCIENCE.value}
        assert res.missing_fields == []

    def test_counselor_note_enquiry_from(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["counselor_enquiry_from"], self.timestamp)
        assert res.name == "Amit Patel"
        assert res.profile_type == ProfileType.FRESHER.value
        assert set(res.technologies) == {Technology.POWER_BI.value}
        assert res.missing_fields == []

    def test_counselor_note_candidate(self):
        res = self.extractor.rule_based_extract(TRANSCRIPTS["counselor_candidate"], self.timestamp)
        assert res.name == "Vikram Malhotra"
        assert res.profile_type == ProfileType.CAREER_SWITCHER.value
        assert set(res.technologies) == {Technology.DATA_SCIENCE.value, Technology.PYTHON.value}
        assert res.missing_fields == []


import asyncio

class TestLLMExtractionWithMock:
    """Verifies that LLM API calls with structured output are properly decoded and normalized."""

    def test_llm_successful_extraction_and_mapping(self):
        async def run_test():
            mock_groq_response = {
                "name": "Siddharth",
                "profile_type": "student",  # Synonym to normalize
                "technologies": ["ML", "PowerBI"]  # Variants to normalize
            }

            service = ExtractionService(api_key="mock_key")

            # Mock Groq client
            with patch("groq.Groq") as mock_groq_class:
                mock_client = MagicMock()
                mock_groq_class.return_value = mock_client

                mock_completion = MagicMock()
                mock_choice = MagicMock()
                mock_choice.message.content = json.dumps(mock_groq_response)
                mock_completion.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_completion

                result = await service.extract_from_transcript(
                    transcript="Hi, I am Siddharth, currently a student looking for ML and PowerBI courses.",
                    enquiry_time="2026-10-12 18:30:00"
                )

                assert result.name == "Siddharth"
                assert result.profile_type == ProfileType.COLLEGE_STUDENT.value
                assert result.technologies == [Technology.AI_ML.value, Technology.POWER_BI.value]
                assert result.missing_fields == []
                assert result.enquiry_time == "2026-10-12 18:30:00"

        asyncio.run(run_test())

    def test_llm_null_values_generate_missing_fields(self):
        async def run_test():
            mock_groq_response = {
                "name": None,
                "profile_type": None,
                "technologies": []
            }

            service = ExtractionService(api_key="mock_key")

            with patch("groq.Groq") as mock_groq_class:
                mock_client = MagicMock()
                mock_groq_class.return_value = mock_client

                mock_completion = MagicMock()
                mock_choice = MagicMock()
                mock_choice.message.content = json.dumps(mock_groq_response)
                mock_completion.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_completion

                result = await service.extract_from_transcript(
                    transcript="Umm, hello? Just wanted to ask a question.",
                    enquiry_time="2026-10-12 18:30:00"
                )

                assert result.name is None
                assert result.profile_type is None
                assert result.technologies == []
                assert set(result.missing_fields) == {"name", "profile_type", "technologies"}

        asyncio.run(run_test())

