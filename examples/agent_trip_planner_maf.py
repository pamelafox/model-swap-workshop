"""
Agent loop: Trip planning with budget constraints (Agent Framework version).

Uses Microsoft Agent Framework's FunctionMiddleware and ChatMiddleware
to log tool calls grouped by turn, showing parallel vs serial patterns.
"""

import asyncio
import json
import os
import warnings
from typing import Annotated

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*experimental.*")

from agent_framework import Agent, ChatContext, ChatMiddleware, FunctionInvocationContext, FunctionMiddleware, tool
from agent_framework_openai import OpenAIChatClient
from dotenv import load_dotenv
from pydantic import Field
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

client = OpenAIChatClient(
    model=deployment_name,
    base_url=endpoint,
    api_key=api_key,
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
def search_flights(
    origin: Annotated[str, Field(description="Origin city code or name.")],
    destination: Annotated[str, Field(description="Destination city code or name.")],
) -> list[dict]:
    """Search for available flights between two cities. Returns a list of flight options with airline, price, stops, and duration."""
    key = f"{origin}-{destination}"
    return FLIGHTS.get(key, FLIGHTS.get("SF-NYC"))


@tool
def search_hotels(
    city: Annotated[str, Field(description="City to search hotels in.")],
    nights: Annotated[int, Field(description="Number of nights to stay.")],
) -> list[dict]:
    """Search for hotels in a city. Returns options with name, price_per_night, rating, and neighborhood. The total cost is price_per_night * nights."""
    results = HOTELS.get(city, HOTELS.get("NYC"))
    return [{**h, "total_cost": h["price_per_night"] * nights} for h in results]


@tool
def check_budget(
    flight_cost: Annotated[float, Field(description="Cost of the selected flight.")],
    hotel_cost: Annotated[float, Field(description="Total cost of the hotel stay.")],
    budget: Annotated[float, Field(description="Total budget limit.")],
) -> dict:
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
def search_activities(
    city: Annotated[str, Field(description="City to search activities in.")],
    max_price: Annotated[float, Field(description="Maximum price for activities. Use the remaining budget after flight and hotel.")],
) -> list[dict]:
    """Search for activities in a city within a price limit. Use the remaining budget after flight and hotel to set max_price."""
    all_activities = ACTIVITIES.get(city, ACTIVITIES.get("NYC"))
    return [a for a in all_activities if a["price"] <= max_price]


# Middleware to log tool calls grouped by turn
pending_calls: list[str] = []
turn_counter = [0]


class LogToolCalls(FunctionMiddleware):
    """Logs each tool call with its arguments."""

    async def process(self, context: FunctionInvocationContext, call_next):
        name = context.function.name
        args = context.arguments
        if isinstance(args, str):
            args = json.loads(args)
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        pending_calls.append(f"[bold cyan]{name}[/]({args_str})")
        await call_next()


class LogTurns(ChatMiddleware):
    """Flushes pending tool calls as a turn group before each model request."""

    async def process(self, context: ChatContext, call_next):
        # Flush pending tool calls from the previous turn
        if pending_calls:
            turn_counter[0] += 1
            label = "parallel" if len(pending_calls) > 1 else "single"
            console.print(f"  [dim]Turn {turn_counter[0]}[/] [dim]({label})[/]")
            for call in pending_calls:
                console.print(f"    {call}")
            pending_calls.clear()
        await call_next()


agent = Agent(
    client=client,
    name="trip-planner",
    instructions=(
        "You are a travel planning assistant. Help users find flights and hotels within their budget. "
        "IMPORTANT RULES:\n"
        "1. Always search for both flights AND hotels before making a recommendation.\n"
        "2. Prefer direct flights over connecting flights when the price difference is less than $100.\n"
        "3. Always call check_budget before giving your final recommendation to verify it fits.\n"
        "4. If nothing fits the budget, say so clearly — do NOT recommend options that exceed the budget.\n"
        "5. If the user asks for activity suggestions, use search_activities with the remaining budget after flight+hotel."
    ),
    tools=[search_flights, search_hotels, check_budget, search_activities],
    middleware=[LogTurns(), LogToolCalls()],
)

USER_MESSAGE = (
    "I need to fly from SF to NYC next month for 3 nights. "
    "My total budget is $600 for flights and hotel combined. "
    "I prefer direct flights if possible. "
    "Also suggest an activity I can do with whatever budget is left over."
)


async def main():
    pending_calls.clear()
    turn_counter[0] = 0
    console.print(f"[bold]Model: {deployment_name}[/]")
    console.print(f"User: {USER_MESSAGE}\n")
    response = await agent.run(USER_MESSAGE)
    # Flush any remaining pending calls
    if pending_calls:
        turn_counter[0] += 1
        label = "parallel" if len(pending_calls) > 1 else "single"
        console.print(f"  [dim]Turn {turn_counter[0]}[/] [dim]({label})[/]")
        for call in pending_calls:
            console.print(f"    {call}")
        pending_calls.clear()
    console.print()
    console.print(Markdown(response.text))


if __name__ == "__main__":
    asyncio.run(main())
