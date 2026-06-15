import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]
deployment_name = "DeepSeek-V4-Flash"

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)


tools = [
    {
        "type": "function",
        "name": "lookup_weather",
        "description": "Lookup the weather for a given city name or zip code.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "The city name",
                },
                "zip_code": {
                    "type": "string",
                    "description": "The zip code",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lookup_movies",
        "description": "Lookup movies playing in a given city name or zip code.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "The city name",
                },
                "zip_code": {
                    "type": "string",
                    "description": "The zip code",
                },
            },
            "additionalProperties": False,
        },
    },
]


# ---------------------------------------------------------------------------
# Tool (function) implementations
# ---------------------------------------------------------------------------
def lookup_weather(city_name: str | None = None, zip_code: str | None = None) -> str:
    """Looks up the weather for given city_name and zip_code."""
    location = city_name or zip_code or "unknown"
    # In a real implementation, call an external weather API here.
    return {
        "location": location,
        "condition": "rain showers",
        "rain_mm_last_24h": 7,
        "recommendation": "Good day for indoor activities if you dislike drizzle.",
    }


def lookup_movies(city_name: str | None = None, zip_code: str | None = None) -> str:
    """Returns a list of movies playing in the given location."""
    location = city_name or zip_code or "unknown"
    # A real implementation could query a cinema listings API.
    return {
        "location": location,
        "movies": [
            {"title": "The Quantum Reef", "rating": "PG-13"},
            {"title": "Storm Over Harbour Bay", "rating": "PG"},
            {"title": "Midnight Koala", "rating": "R"},
        ],
    }


tool_mapping = {
    "lookup_weather": lookup_weather,
    "lookup_movies": lookup_movies,
}


# ---------------------------------------------------------------------------
# Conversation loop
# ---------------------------------------------------------------------------
messages = [
    {"role": "system", "content": "You are a tourism chatbot."},
    {"role": "user", "content": "Is it rainy enough in Sydney to watch movies and which ones are on?"},
]

while True:
    print("Calling model...\n")
    response = client.responses.create(
        model=deployment_name,
        input=messages,  # includes prior tool outputs
        tools=tools,
        tool_choice="auto",
        store=False,
    )

    tool_calls = [item for item in response.output if item.type == "function_call"]
    # If the assistant returned standard content with no tool calls, we're done.
    if not tool_calls:
        print("Assistant:")
        print(response.output_text)
        break

    # Append the function call items as plain dicts (avoid SDK objects with IDs
    # that require server-side persistence via store=True).
    for item in response.output:
        item_dict = item.model_dump(exclude_none=True)
        item_dict.pop("id", None)
        messages.append(item_dict)

    # Execute each requested tool sequentially.
    for tool_call in tool_calls:
        fn_name = tool_call.name
        raw_args = tool_call.arguments or "{}"
        print(f"Tool request: {fn_name}({raw_args})")
        target_tool = tool_mapping.get(fn_name)
        parsed_args = json.loads(raw_args)
        tool_result = target_tool(**parsed_args)
        tool_result_str = json.dumps(tool_result)
        # Provide the tool output back to the model
        messages.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": tool_result_str,
            }
        )