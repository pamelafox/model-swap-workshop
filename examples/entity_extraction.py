import os
import warnings

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import rich
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]
# Verified for strict structured output via responses.parse: DeepSeek-V4-Flash, DeepSeek-V4-Pro, gpt-5.5.
# Kimi-K2.6 may return markdown-style text instead of JSON and fail validation.
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


messages = [
    {
        "role": "system",
        "content": (
            "Extract one calendar event from the user message. "
            "Return name, date, and participants."
        ),
    },
    {
        "role": "user",
        "content": "Alice and Bob are going to a science fair on Friday.",
    },
]

# Preferred path: typed parsing directly from the Responses API.
response = client.responses.parse(
    model=deployment_name,
    input=messages,
    text_format=CalendarEvent,
    store=False,
    #reasoning={"effort": "none"}
)
if response.output_parsed:
    rich.print(response.output_parsed)
else:
    rich.print(response.output[0].content[0].refusal)