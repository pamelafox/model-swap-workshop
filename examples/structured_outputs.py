"""
Structured output extraction: Extract travel itinerary details from a natural
language email. Tests whether models can reliably populate a schema with
inferred fields (passenger count, airport codes, dates).
"""

import os
import warnings

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import json

from enum import Enum

import rich
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

MODEL = "gpt-5.5"
# MODEL = "Mistral-Large-3"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)


class TripType(str, Enum):
    roundtrip = "roundtrip"
    one_way = "one_way"
    multi_city = "multi_city"


class CabinClass(str, Enum):
    economy = "economy"
    business = "business"
    first = "first"


class FlightBooking(BaseModel):
    origin_airport: str
    destination_airport: str
    departure_date: str
    return_date: str
    num_passengers: int
    trip_type: TripType
    cabin_class: CabinClass


SYSTEM_PROMPT = "Extract the flight booking details from the user's message. Today is Sunday, June 15, 2026."

USER_PROMPT = """\
My college roommates and I (4 of us total) are planning a reunion trip! \
We want to splurge on business class from San Francisco to Tokyo. \
Thinking of leaving next Tuesday and staying through the weekend — \
flying back that Monday."""


if deployment_name.startswith("gpt-"):
    # GPT models support strict structured output via responses.parse
    response = client.responses.parse(
        model=deployment_name,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        text_format=FlightBooking,
        store=False,
    )
    if response.output_parsed:
        rich.print(response.output_parsed)
    else:
        rich.print(response.output_text)
else:
    # Other models: use function calling as a structured output mechanism
    tools = [
        {
            "type": "function",
            "name": "extract_flight_booking",
            "description": "Extract flight booking details from the user message.",
            "parameters": FlightBooking.model_json_schema(),
        }
    ]
    response = client.responses.create(
        model=deployment_name,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_flight_booking function with the extracted info."},
            {"role": "user", "content": USER_PROMPT},
        ],
        tools=tools,
        tool_choice="required",
        store=False,
    )
    tool_call = next((item for item in response.output if item.type == "function_call"), None)
    if tool_call:
        result = FlightBooking.model_validate_json(tool_call.arguments)
        rich.print(result)
    else:
        print(f"No tool call made. Response: {response.output_text[:200]}")
