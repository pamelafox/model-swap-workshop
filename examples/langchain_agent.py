import os
import random
from datetime import datetime

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.tools import tool

load_dotenv(override=True)

azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])

provider = os.environ.get("MODEL_CHOICE", "openai")
if provider == "openai":
    model = AzureAIOpenAIApiChatModel(
        endpoint=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1",
        credential=azure_credential,
        model=os.environ["FOUNDRY_OPENAI_DEPLOYMENT"],
        use_responses_api=True,
    )
elif provider == "claude":
    token_provider = get_bearer_token_provider(azure_credential, "https://ai.azure.com/.default")
    # Warning: token_provider() returns a token valid for ~1 hour.
    # For long-running services, call token_provider() again before each agent run.
    # Azure Foundry expects Authorization: Bearer header, not x-api-key.
    model = ChatAnthropic(
        model=os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"],
        base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic",
        api_key="placeholder",
        default_headers={"Authorization": f"Bearer {token_provider()}"},
    )


@tool
def get_weather(city: str, date: str) -> dict:
    """Returns weather data for a given city and date."""
    if random.random() < 0.05:
        return {"temperature": 72, "description": "Sunny"}
    else:
        return {"temperature": 60, "description": "Rainy"}


@tool
def get_activities(city: str, date: str) -> list:
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


agent = create_agent(
    model=model,
    system_prompt=(
        "You help users plan their weekends and choose the best activities for the given weather. "
        "If an activity would be unpleasant in weather, don't suggest it. Include date of the weekend in response."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


def main():
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "what can I do this weekend in San Francisco?"}]}
    )
    latest_message = response["messages"][-1]
    print(latest_message.content)


if __name__ == "__main__":
    main()
