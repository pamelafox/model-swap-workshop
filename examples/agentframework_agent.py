import asyncio
import os
import random
from datetime import datetime
from typing import Annotated

from anthropic import AsyncAnthropic
from anthropic.lib.credentials import AccessToken
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv
from agent_framework_openai import OpenAIChatClient
from agent_framework.anthropic import AnthropicClient
from agent_framework import Agent, tool
from pydantic import Field

load_dotenv(override=True)

azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])

provider = os.environ.get("MODEL_CHOICE", "claude")

if provider == "openai":

    client = OpenAIChatClient(
        model=os.environ["FOUNDRY_OPENAI_DEPLOYMENT"],
        azure_endpoint=os.environ["FOUNDRY_MODELS_ENDPOINT"],
        credential=azure_credential,
    )

elif provider == "claude":

    def _entra_credentials_provider(scope: str = "https://ai.azure.com/.default"):
        def _provider(*, force_refresh: bool = False) -> AccessToken:
            token = azure_credential.get_token(scope)
            return AccessToken(token=token.token, expires_at=token.expires_on)
        return _provider

    client = AnthropicClient(
        model=os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"],
        anthropic_client=AsyncAnthropic(
            credentials=_entra_credentials_provider(),
            base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic",
        ),
    )

@tool
def get_weather(
    city: Annotated[str, Field(description="The city to get the weather for.")],
) -> dict:
    """Returns weather data for a given city, a dictionary with temperature and description."""
    if random.random() < 0.05:
        return {"temperature": 72, "description": "Sunny"}
    else:
        return {"temperature": 60, "description": "Rainy"}


@tool
def get_activities(
    city: Annotated[str, Field(description="The city to get activities for.")],
    date: Annotated[str, Field(description="The date to get activities for in format YYYY-MM-DD.")],
) -> list[dict]:
    """Returns a list of activities for a given city and date."""
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]


@tool
def get_current_date() -> str:
    """Gets the current date from the system and returns as a string in format YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


agent = Agent(
    client=client,
    name="weekend-planner",
    instructions=(
        "You help users plan their weekends and choose the best activities for the given weather. "
        "If an activity would be unpleasant in weather, don't suggest it. Include date of the weekend in response."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def main():
    response = await agent.run("what can I do this weekend in San Francisco?")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
