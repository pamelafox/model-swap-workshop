import os
import warnings

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import pymupdf4llm
import rich
from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

api_type = os.environ.get("API_TYPE", "openai_responses")


# Define models for Structured Outputs
class Item(BaseModel):
    product: str
    price: float
    quantity: int


class Receipt(BaseModel):
    total: float
    shipping: float
    payment_method: str
    items: list[Item]
    order_number: int


SYSTEM_PROMPT = "Extract the information from the receipt"

# Prepare PDF as markdown text
md_text = pymupdf4llm.to_markdown("example_receipt.pdf")

if api_type == "openai_responses":
    endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
    api_key = os.environ["FOUNDRY_API_KEY"]
    deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

    client = OpenAI(
        base_url=endpoint,
        api_key=api_key,
    )

    # gpt-* models support strict structured output via responses.parse.
    # Other models don't enforce text_format, so use function calling instead.
    if deployment_name.startswith("gpt-"):
        response = client.responses.parse(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": md_text},
            ],
            text_format=Receipt,
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
                "name": "extract_receipt",
                "description": "Extract structured info from a receipt.",
                "parameters": Receipt.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_receipt function with the extracted info."},
                {"role": "user", "content": md_text},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next(item for item in response.output if item.type == "function_call")
        result = Receipt.model_validate_json(tool_call.arguments)
        rich.print(result)

elif api_type == "anthropic_messages":
    endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic"
    api_key = os.environ["FOUNDRY_ANTHROPIC_API_KEY"]
    deployment_name = os.environ["FOUNDRY_ANTHROPIC_CLAUDE_DEPLOYMENT"]

    client = Anthropic(
        api_key=api_key,
        base_url=endpoint,
    )

    response = client.messages.parse(
        model=deployment_name,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": md_text}],
        output_format=Receipt,
    )
    rich.print(response.parsed_output)
