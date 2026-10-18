"""Azure OpenAI helpers and TalentIQ prompts."""
from __future__ import annotations

import json
import os
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
REASONING_EFFORT = os.getenv("REASONING_EFFORT")
_client: Any = None

JD_SYSTEM = """You are a recruitment analyst. Extract structured data from the job description.
Return JSON with exactly these keys: role, must_have_skills, nice_to_have_skills, experience,
location, education, domain. Lists must be lists of strings. If not stated write "Not stated".
Never guess."""
RANK_SYSTEM = """You are a fair, evidence-based CV screener. Score one CV against job requirements
out of 100: skills 40, relevant experience 30, domain 15, education/certifications 10,
achievements 5. Ignore name, gender, age, photo, marital status, religion, nationality and address.
Use only evidence in the CV. Return JSON: score integer, reason (two short sentences),
matched_skills list, missing_skills list, evidence (one short quote)."""
QUESTIONS_SYSTEM = """Create exactly 10 phone-screening questions: 4 Technical, 3 Experience,
3 Fit. Return JSON {"questions":[{"type":"","question":"","good_answer":""}]}."""
MARKET_SYSTEM = """You are a hiring-market analyst for India. Return JSON {"insights":[...]} with
6 to 8 companies, experience_range, compensation_range_inr, hiring_location, source, is_estimate.
Never invent URLs; estimates must say so in source."""
SEARCH_SYSTEM = """Return JSON with keys naukri_boolean, naukri_plain, linkedin_boolean, linkedin_plain.
Boolean versions use AND, OR, NOT, quotes and parentheses; plain versions are simple keywords."""


def get_client() -> Any:
    global _client
    if _client is not None:
        return _client
    if API_KEY and ENDPOINT:
        _client = AzureOpenAI(azure_endpoint=ENDPOINT, api_key=API_KEY, api_version=API_VERSION)
    elif PROJECT_ENDPOINT:
        from azure.ai.projects import AIProjectClient
        _client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential()).get_openai_client()
    elif ENDPOINT:
        provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        _client = AzureOpenAI(azure_endpoint=ENDPOINT, azure_ad_token_provider=provider, api_version=API_VERSION)
    else:
        raise RuntimeError("Azure configuration is missing.")
    return _client


def ask(system: str, user: str, as_json: bool = False) -> Any:
    if not DEPLOYMENT:
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is missing.")
    kwargs: dict[str, Any] = {"response_format": {"type": "json_object"}} if as_json else {}
    if REASONING_EFFORT:
        kwargs["reasoning_effort"] = REASONING_EFFORT
    response = get_client().chat.completions.create(
        model=DEPLOYMENT,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    text = response.choices[0].message.content or ""
    if not as_json:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The model returned invalid JSON.") from exc
