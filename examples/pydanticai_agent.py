import asyncio
import os
import random
from datetime import datetime

from anthropic import AsyncAnthropic
from anthropic.lib.credentials import AccessToken
from azure.identity import AzureDeveloperCliCredential as SyncAzureDeveloperCliCredential
from azure.identity.aio import AzureDeveloperCliCredential as AsyncAzureDeveloperCliCredential
from azure.identity.aio import get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

load_dotenv(override=True)

provider = os.environ.get("MODEL_CHOICE", "openai")

if provider == "openai":
    async_azure_credential = AsyncAzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    token_provider = get_bearer_token_provider(async_azure_credential, "https://ai.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
    model = OpenAIChatModel(os.environ["FOUNDRY_OPENAI_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))

elif provider == "claude":
    sync_azure_credential = SyncAzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])

    def anthropic_credentials_provider():
        def _provider(*, force_refresh: bool = False) -> AccessToken:
            token = sync_azure_credential.get_token("https://ai.azure.com/.default")
            return AccessToken(token=token.token, expires_at=token.expires_on)
        return _provider

    foundry_client = AsyncAnthropic(
        credentials=anthropic_credentials_provider(),
        base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic",
    )
    model = AnthropicModel(
        os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"],
        provider=AnthropicProvider(anthropic_client=foundry_client),
    )
else:
    raise ValueError(f"Unsupported MODEL_CHOICE: {provider}")


def get_weather(city: str) -> dict:
    """Returns weather data for a given city, a dictionary with temperature and description."""
    if random.random() < 0.05:
        return {"city": city, "temperature": 72, "description": "Sunny"}
    else:
        return {"city": city, "temperature": 60, "description": "Rainy"}

def get_activities(city: str, date: str) -> list:
    """Returns a list of activities for a given city and date."""
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]

def get_current_date() -> str:
    """Gets the current date from the system and returns as a string in format YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


agent = Agent(
    model,
    system_prompt=(
        "You help users plan their weekends and choose the best activities for the given weather. "
        "If an activity would be unpleasant in the weather, don't suggest it. "
        "Include the date of the weekend in your response."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def main():
    result = await agent.run("what can I do this weekend in San Francisco?")
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
