"""
Agent loop: Trip planning with budget constraints (LangChain version).

Uses LangChain's AgentMiddleware (awrap_tool_call + abefore_model)
to log tool calls grouped by turn, showing parallel vs serial patterns.
"""

import json
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.tools import tool
from rich.console import Console
from rich.markdown import Markdown

load_dotenv()

console = Console(highlight=False)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
# MODEL = "Mistral-Large-3"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

model = AzureAIOpenAIApiChatModel(
    endpoint=endpoint + "/openai/v1",
    api_key=api_key,
    model=deployment_name,
    use_responses_api=True,
)

# Fake data for tools
FLIGHTS = {
    "SF-NYC": [
        {"airline": "United", "price": 280, "stops": 0, "duration": "5h30m"},
        {"airline": "Delta", "price": 195, "stops": 1, "duration": "8h15m"},
        {"airline": "JetBlue", "price": 320, "stops": 0, "duration": "5h20m"},
    ],
}

HOTELS = {
    "NYC": [
        {"name": "The Pod Hotel", "price_per_night": 95, "rating": 4.2, "neighborhood": "Midtown"},
        {"name": "Hotel Indigo", "price_per_night": 210, "rating": 4.5, "neighborhood": "Brooklyn"},
        {"name": "The Jane", "price_per_night": 135, "rating": 4.0, "neighborhood": "West Village"},
        {"name": "Ace Hotel", "price_per_night": 275, "rating": 4.6, "neighborhood": "NoMad"},
    ],
}

ACTIVITIES = {
    "NYC": [
        {"name": "Broadway Show", "price": 85, "category": "entertainment"},
        {"name": "Statue of Liberty Tour", "price": 25, "category": "sightseeing"},
        {"name": "Museum of Modern Art", "price": 30, "category": "culture"},
        {"name": "Central Park Bike Tour", "price": 45, "category": "outdoors"},
        {"name": "Food Tour - Greenwich Village", "price": 65, "category": "food"},
    ],
}


@tool
def search_flights(origin: str, destination: str) -> list[dict]:
    """Search for available flights between two cities. Returns a list of flight options with airline, price, stops, and duration."""
    key = f"{origin}-{destination}"
    return FLIGHTS.get(key, FLIGHTS.get("SF-NYC"))


@tool
def search_hotels(city: str, nights: int) -> list[dict]:
    """Search for hotels in a city. Returns options with name, price_per_night, rating, and neighborhood. The total cost is price_per_night * nights."""
    results = HOTELS.get(city, HOTELS.get("NYC"))
    return [{**h, "total_cost": h["price_per_night"] * nights} for h in results]


@tool
def check_budget(flight_cost: float, hotel_cost: float, budget: float) -> dict:
    """Check if the selected flight + hotel fits within the budget. Returns whether it's within budget and the remaining amount."""
    total = flight_cost + hotel_cost
    within_budget = total <= budget
    return {
        "total_cost": total,
        "budget": budget,
        "within_budget": within_budget,
        "remaining": budget - total,
    }


@tool
def search_activities(city: str, max_price: float) -> list[dict]:
    """Search for activities in a city within a price limit. Use the remaining budget after flight and hotel to set max_price."""
    all_activities = ACTIVITIES.get(city, ACTIVITIES.get("NYC"))
    return [a for a in all_activities if a["price"] <= max_price]


# Middleware to log tool calls grouped by turn
class ToolCallLogger(AgentMiddleware):
    def __init__(self):
        self.pending_calls: list[str] = []
        self.turn = 0

    def before_model(self, state, runtime):
        # Flush pending tool calls from the previous turn
        if self.pending_calls:
            self.turn += 1
            label = "parallel" if len(self.pending_calls) > 1 else "single"
            console.print(f"  [dim]Turn {self.turn}[/] [dim]({label})[/]")
            for call in self.pending_calls:
                console.print(f"    {call}")
            self.pending_calls = []

    def wrap_tool_call(self, request, handler):
        tool_call = request.tool_call
        name = tool_call["name"]
        args = tool_call.get("args", {})
        if isinstance(args, str):
            args = json.loads(args)
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        self.pending_calls.append(f"[bold cyan]{name}[/]({args_str})")
        return handler(request)


logger = ToolCallLogger()

agent = create_agent(
    model=model,
    system_prompt=(
        "You are a travel planning assistant. Help users find flights and hotels within their budget. "
        "IMPORTANT RULES:\n"
        "1. Always search for both flights AND hotels before making a recommendation.\n"
        "2. Prefer direct flights over connecting flights when the price difference is less than $100.\n"
        "3. Always call check_budget before giving your final recommendation to verify it fits.\n"
        "4. If nothing fits the budget, say so clearly — do NOT recommend options that exceed the budget.\n"
        "5. If the user asks for activity suggestions, use search_activities with the remaining budget after flight+hotel."
    ),
    tools=[search_flights, search_hotels, check_budget, search_activities],
    middleware=[logger],
)

USER_MESSAGE = (
    "I need to fly from SF to NYC next month for 3 nights. "
    "My total budget is $600 for flights and hotel combined. "
    "I prefer direct flights if possible. "
    "Also suggest an activity I can do with whatever budget is left over."
)


def main():
    logger.pending_calls = []
    logger.turn = 0
    console.print(f"[bold]Model: {deployment_name}[/]")
    console.print(f"User: {USER_MESSAGE}\n")
    response = agent.invoke({"messages": [{"role": "user", "content": USER_MESSAGE}]})
    # Flush any remaining pending calls
    if logger.pending_calls:
        logger.turn += 1
        label = "parallel" if len(logger.pending_calls) > 1 else "single"
        console.print(f"  [dim]Turn {logger.turn}[/] [dim]({label})[/]")
        for call in logger.pending_calls:
            console.print(f"    {call}")
    console.print()
    latest_message = response["messages"][-1]
    console.print(Markdown(latest_message.text))


if __name__ == "__main__":
    main()
