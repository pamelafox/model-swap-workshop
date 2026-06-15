import os
import warnings
from enum import Enum

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import requests
import rich
from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

api_type = os.environ.get("API_TYPE", "openai_responses")


# Define models for Structured Outputs
class IssueType(str, Enum):
    BUGREPORT = "Bug Report"
    FEATURE = "Feature"
    DOCUMENTATION = "Documentation"
    REGRESSION = "Regression"


class Issue(BaseModel):
    title: str
    description: str = Field(..., description="A 1-2 sentence description of the project")
    type: IssueType
    operating_system: str


SYSTEM_PROMPT = "Extract the info from the GitHub issue markdown."

# Fetch an issue from a public GitHub repository
url = "https://api.github.com/repos/Azure-Samples/azure-search-openai-demo/issues/2231"
response = requests.get(url)
if response.status_code != 200:
    print(f"Failed to fetch issue: {response.status_code}")
    exit(1)
issue_body = response.json()["body"]

if api_type == "openai_responses":
    endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
    api_key = os.environ["FOUNDRY_API_KEY"]
    deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]

    client = OpenAI(
        base_url=endpoint,
        api_key=api_key,
    )

    # DeepSeek, Kimi, and Mistral don't enforce text_format for complex schemas, so use function calling instead.
    if deployment_name in ("DeepSeek-V4-Flash", "DeepSeek-V4-Pro", "Kimi-K2.6", "Mistral-Large-3"):
        tools = [
            {
                "type": "function",
                "name": "extract_issue",
                "description": "Extract structured info from a GitHub issue.",
                "parameters": Issue.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_issue function with the extracted info."},
                {"role": "user", "content": issue_body},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next(item for item in response.output if item.type == "function_call")
        result = Issue.model_validate_json(tool_call.arguments)
        rich.print(result)
    else:
        response = client.responses.parse(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": issue_body},
            ],
            text_format=Issue,
            store=False,
        )
        if response.output_parsed:
            rich.print(response.output_parsed)
        else:
            rich.print(response.output[0].content[0].refusal)

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
        messages=[{"role": "user", "content": issue_body}],
        output_format=Issue,
    )
    rich.print(response.parsed_output)
