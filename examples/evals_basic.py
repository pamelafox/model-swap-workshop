"""
Basic evaluations: Run verifiable test cases across models and check correctness.

Tests cases with deterministic ground-truth answers:
- Letter counting (correct: 13)
- Spatial reasoning (correct: Southeast)
- Structured outputs (correct dates, IATA codes)
- Tool calling (correct attendee normalization, location format)

No eval framework needed — just programmatic checks.

Usage:
    uv run examples/evals_basic.py
"""

import json
import os
import re

os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import warnings

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(base_url=endpoint, api_key=api_key)

MODELS = [
    "gpt-5.5",
    "Kimi-K2.6",
    "Mistral-Large-3",
    "DeepSeek-V4-Flash",
]


# ---------------------------------------------------------------------------
# Helper: extract text from a Responses API output
# ---------------------------------------------------------------------------
def extract_text(response) -> str:
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    return content.text
    return ""


# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------

def eval_letter_counting(model: str) -> dict:
    """Count letter 'e' in a sentence. Correct answer: 13."""
    prompt = (
        'How many times does the letter "e" appear in the following sentence? '
        "Count carefully.\n"
        '"The elderly gentleman eagerly entered the elevator."\n'
        "Give just the number."
    )
    response = client.responses.create(model=model, input=prompt, store=False)
    text = extract_text(response)
    # Extract the first number from the response
    numbers = re.findall(r"\d+", text)
    answer = int(numbers[0]) if numbers else None
    return {
        "test": "letter_counting",
        "expected": 13,
        "actual": answer,
        "pass": answer == 13,
        "raw": text.strip()[:80],
    }


def eval_spatial_reasoning(model: str) -> dict:
    """Multi-step rotation. Correct answer: Southeast."""
    prompt = (
        "I am standing in the center of a room facing north. "
        "I turn right 90 degrees. I turn right 90 degrees again. "
        "I turn left 45 degrees. "
        "What compass direction am I now facing? "
        "Answer with just the direction and a one-sentence explanation."
    )
    response = client.responses.create(model=model, input=prompt, store=False)
    text = extract_text(response).lower()
    # Check that the answer starts with "southeast" (before the explanation)
    first_line = text.strip().split("\n")[0].split(".")[0].strip()
    passed = "southeast" in first_line
    return {
        "test": "spatial_reasoning",
        "expected": "Southeast",
        "actual": text.strip()[:80],
        "pass": passed,
    }


def eval_structured_output(model: str) -> dict:
    """Extract flight booking with correct dates and IATA codes."""
    from enum import Enum

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

    system = "Extract the flight booking details from the user's message. Today is Monday, June 29, 2026."
    user = (
        "My college roommates and I (4 of us total) are planning a reunion trip! "
        "We want to splurge on business class from San Francisco to Tokyo. "
        "Thinking of leaving this Saturday and coming back the following Friday."
    )

    parsed = None
    if model.startswith("gpt-"):
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=FlightBooking,
            store=False,
        )
        if response.output_parsed:
            parsed = response.output_parsed
    else:
        tools = [
            {
                "type": "function",
                "name": "extract_flight_booking",
                "description": "Extract flight booking details from the user message.",
                "parameters": FlightBooking.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system + " Call the extract_flight_booking function with the extracted info."},
                {"role": "user", "content": user},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next((item for item in response.output if item.type == "function_call"), None)
        if tool_call:
            try:
                parsed = FlightBooking.model_validate_json(tool_call.arguments)
            except Exception:
                parsed = None

    if not parsed:
        return {
            "test": "structured_output",
            "expected": "SFO/NRT/2026-07-04/2026-07-10/4",
            "actual": "PARSE_FAILED",
            "pass": False,
        }

    checks = {
        "origin_is_SFO": parsed.origin_airport == "SFO",
        "dest_is_IATA": len(parsed.destination_airport) == 3 and parsed.destination_airport.isupper(),
        "departure_2026-07-04": parsed.departure_date == "2026-07-04",
        "return_2026-07-10": parsed.return_date == "2026-07-10",
        "passengers_4": parsed.num_passengers == 4,
        "cabin_business": parsed.cabin_class == CabinClass.business,
    }
    all_pass = all(checks.values())
    actual = f"{parsed.origin_airport}/{parsed.destination_airport}/{parsed.departure_date}/{parsed.return_date}/{parsed.num_passengers}"
    return {
        "test": "structured_output",
        "expected": "SFO/<IATA>/2026-07-04/2026-07-10/4",
        "actual": actual,
        "pass": all_pass,
        "checks": checks,
    }


def eval_tool_calling(model: str) -> dict:
    """Create a calendar event with correct argument normalization."""
    tools = [
        {
            "type": "function",
            "name": "create_calendar_event",
            "description": "Create a calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title in Title Case (e.g. 'Weekly Standup', 'Q3 Planning')"},
                    "start_time": {"type": "string", "description": "Start time in ISO 8601 format with timezone offset (e.g. 2026-07-01T14:00:00-07:00)"},
                    "end_time": {"type": "string", "description": "End time in ISO 8601 format with timezone offset (e.g. 2026-07-01T15:00:00-07:00)"},
                    "timezone": {"type": "string", "description": "IANA timezone identifier (e.g. 'America/Los_Angeles', 'America/New_York')"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee names only"},
                    "location": {"type": "string", "description": "Room name, or 'Virtual' for online meetings"},
                    "duration_minutes": {"type": "integer", "description": "Duration of the meeting in minutes"},
                },
                "required": ["title", "start_time", "end_time", "timezone"],
                "additionalProperties": False,
            },
        },
    ]
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You are a helpful calendar assistant. Today is Monday, June 29, 2026. Use the available tools to process the user's request."},
            {"role": "user", "content": "Can you throw something on my calendar? Platform team sync — me, Sarah from eng, Marcus, and that new PM Priya. Tomorrow at 1:30 PT for a half hour. It's virtual, on Microsoft Teams."},
        ],
        tools=tools,
        store=False,
    )
    tool_call = next((item for item in response.output if item.type == "function_call"), None)
    if not tool_call:
        return {
            "test": "tool_calling",
            "expected": "attendees=[Sarah,Marcus,Priya], location=Virtual",
            "actual": "NO_TOOL_CALL",
            "pass": False,
        }

    args = json.loads(tool_call.arguments)
    attendees = args.get("attendees", [])
    location = args.get("location", "")
    # Check: "me" should not be in attendees, location should be exactly "Virtual"
    no_me = not any(a.lower() in ("me", "you") for a in attendees)
    location_correct = location == "Virtual"
    start_correct = args.get("start_time", "").startswith("2026-06-30T13:30")
    return {
        "test": "tool_calling",
        "expected": "attendees=[Sarah,Marcus,Priya], location=Virtual",
        "actual": f"attendees={attendees}, location={location}",
        "pass": no_me and location_correct and start_correct,
    }


# ---------------------------------------------------------------------------
# Run all evals
# ---------------------------------------------------------------------------
EVAL_FUNCTIONS = [
    eval_letter_counting,
    eval_spatial_reasoning,
    eval_structured_output,
    eval_tool_calling,
]


def main():
    results = []
    for model in MODELS:
        print(f"\n{'='*60}")
        print(f"  Evaluating: {model}")
        print(f"{'='*60}")
        for eval_fn in EVAL_FUNCTIONS:
            try:
                result = eval_fn(model)
                result["model"] = model
                results.append(result)
                status = "✅ PASS" if result["pass"] else "❌ FAIL"
                print(f"  {status}  {result['test']:20s}  actual={result['actual']}")
            except Exception as e:
                results.append({"model": model, "test": eval_fn.__name__.replace("eval_", ""), "pass": False, "error": str(e)})
                print(f"  💥 ERROR {eval_fn.__name__}: {e}")

    # Summary table
    print(f"\n\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<20} {'Passed':<8} {'Failed':<8} {'Score'}")
    print(f"{'-'*20} {'-'*8} {'-'*8} {'-'*8}")
    for model in MODELS:
        model_results = [r for r in results if r["model"] == model]
        passed = sum(1 for r in model_results if r.get("pass"))
        failed = len(model_results) - passed
        score = f"{passed}/{len(model_results)}"
        print(f"{model:<20} {passed:<8} {failed:<8} {score}")


if __name__ == "__main__":
    main()
