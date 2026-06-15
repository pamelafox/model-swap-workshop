import os

from dotenv import load_dotenv
from openai import OpenAI

# Setup the OpenAI client to use either Azure, OpenAI.com, or Ollama API
load_dotenv()
API_HOST = os.getenv("API_HOST", "azure")

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

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
    }
]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

response = client.responses.create(
    model=deployment_name,
    input=[
        {"role": "system", "content": "You are a weather chatbot."},
        {"role": "user", "content": "Hi, whats the weather like in berkeley?"},
    ],
    tools=tools,
    store=False,
)

print(f"Response from {deployment_name} on {API_HOST}: \n")

tool_calls = [item for item in response.output if item.type == "function_call"]
if tool_calls:
    tool_call = tool_calls[0]
    print(tool_call.name)
    print(tool_call.arguments)
else:
    print(response.output_text)