import os
import warnings

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import rich
from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

api_type = os.environ.get("API_TYPE", "openai_responses")


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

SYSTEM_PROMPT = (
    "Extract one calendar event from the user message. "
    "Return name, date, and participants."
)
USER_PROMPT = "Alice and Bob are going to a science fair on Friday."

if api_type == "openai_responses":
    endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
    api_key = os.environ["FOUNDRY_API_KEY"]
    # gpt-* models support strict structured output via responses.parse.
    # Other models don't enforce text_format, so use function calling instead.
    deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

    client = OpenAI(
        base_url=endpoint,
        api_key=api_key,
    )

    if deployment_name.startswith("gpt-"):
        response = client.responses.parse(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            text_format=CalendarEvent,
            store=False,
        )
        if response.output_parsed:
            rich.print(response.output_parsed)
        else:
            rich.print(response.output[0].content[0].refusal)
    else:
        tools = [
            {
                "type": "function",
                "name": "extract_calendar_event",
                "description": "Extract a calendar event from the user message.",
                "parameters": CalendarEvent.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_calendar_event function with the extracted info."},
                {"role": "user", "content": USER_PROMPT},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next(item for item in response.output if item.type == "function_call")
        result = CalendarEvent.model_validate_json(tool_call.arguments)
        rich.print(result)

elif api_type == "anthropic_messages":
    endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic"
    api_key = os.environ["FOUNDRY_ANTHROPIC_API_KEY"]
    deployment_name = "claude-sonnet-4-5"

    client = Anthropic(
        api_key=api_key,
        base_url=endpoint,
    )

    response = client.messages.parse(
        model=deployment_name,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
        output_format=CalendarEvent,
    )
    rich.print(response.parsed_output)