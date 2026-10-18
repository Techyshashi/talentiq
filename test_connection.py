"""Verify TalentIQ Azure authentication and model connectivity."""
import os

from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

if not deployment:
    raise SystemExit("Missing AZURE_OPENAI_DEPLOYMENT in .env")

if api_key:
    if not endpoint:
        raise SystemExit("Missing AZURE_OPENAI_ENDPOINT for API-key mode")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    print("Auth mode: API key + direct endpoint")
elif project_endpoint:
    try:
        from azure.ai.projects import AIProjectClient
    except ImportError as exc:
        raise SystemExit(
            "azure-ai-projects is not installed; install approved dependencies first."
        ) from exc
    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    client = project.get_openai_client()
    print("Auth mode: Foundry project endpoint + az login")
elif endpoint:
    provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=provider,
        api_version=api_version,
    )
    print("Auth mode: direct endpoint + az login")
else:
    raise SystemExit(
        "Missing Azure configuration. Set AZURE_AI_PROJECT_ENDPOINT, or set "
        "AZURE_OPENAI_ENDPOINT with AZURE_OPENAI_API_KEY."
    )

print("Deployment:", deployment)
response = client.chat.completions.create(
    model=deployment,
    messages=[{"role": "user", "content": "Reply with the single word: connected"}],
)
print("Model replied:", response.choices[0].message.content)
