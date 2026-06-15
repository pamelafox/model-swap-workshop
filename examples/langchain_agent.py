import os
import random
from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.tools import tool

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

model = AzureAIOpenAIApiChatModel(
    endpoint=endpoint + "/openai/v1",
    api_key=api_key,
    model=deployment_name,
    use_responses_api=True,
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
    print(latest_message.text)


if __name__ == "__main__":
    main()
