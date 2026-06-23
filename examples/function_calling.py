import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

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

tools = [
    {
        "type": "function",
        "name": "book_flight",
        "description": "Book a flight between two cities.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin_airport": {
                    "type": "string",
                    "description": "IATA airport code for departure (e.g. SFO, JFK)",
                },
                "destination_airport": {
                    "type": "string",
                    "description": "IATA airport code for arrival (e.g. LHR, NRT)",
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date in YYYY-MM-DD format",
                },
                "return_date": {
                    "type": "string",
                    "description": "Return date in YYYY-MM-DD format, or empty for one-way",
                },
                "num_passengers": {
                    "type": "integer",
                    "description": "Number of passengers",
                },
            },
            "required": ["origin_airport", "destination_airport", "departure_date", "num_passengers"],
            "additionalProperties": False,
        },
    },
]

USER_MESSAGE = (
    "Book a round-trip flight for 3 people from Los Angeles to Tokyo, "
    "departing next Tuesday and returning the following Monday."
)

response = client.responses.create(
    model=deployment_name,
    input=[
        {"role": "system", "content": "You are a travel booking assistant. Use the available tools to help the user. Today is Sunday, June 15, 2026."},
        {"role": "user", "content": USER_MESSAGE},
    ],
    tools=tools,
    store=False,
)

print(f"Response from {deployment_name}:\n")
tool_calls = [item for item in response.output if item.type == "function_call"]
if tool_calls:
    print(f"Made {len(tool_calls)} tool call(s):")
    for tool_call in tool_calls:
        print(f"  {tool_call.name}({tool_call.arguments})")
else:
    print(response.output_text)