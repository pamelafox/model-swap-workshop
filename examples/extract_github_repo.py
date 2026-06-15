import base64
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
class Language(str, Enum):
    JAVASCRIPT = "JavaScript"
    PYTHON = "Python"
    DOTNET = ".NET"


class AzureService(str, Enum):
    AISTUDIO = "AI Studio"
    AISEARCH = "AI Search"
    POSTGRESQL = "PostgreSQL"
    COSMOSDB = "CosmosDB"
    AZURESQL = "Azure SQL"


class Framework(str, Enum):
    LANGCHAIN = "Langchain"
    SEMANTICKERNEL = "Semantic Kernel"
    LLAMAINDEX = "Llamaindex"
    AUTOGEN = "Autogen"
    SPRINGBOOT = "Spring Boot"
    PROMPTY = "Prompty"


class RepoOverview(BaseModel):
    name: str
    description: str = Field(..., description="A 1-2 sentence description of the project")
    languages: list[Language]
    azure_services: list[AzureService]
    frameworks: list[Framework]


SYSTEM_PROMPT = "Extract the information from the GitHub repository README markdown about this project."

# Fetch a README from a public GitHub repository
url = "https://api.github.com/repos/shank250/CareerCanvas-msft-raghack/contents/README.md"
response = requests.get(url)
if response.status_code != 200:
    print(f"Failed to fetch README: {response.status_code}")
    exit(1)
content = response.json()
readme_content = base64.b64decode(content["content"]).decode("utf-8")

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
                "name": "extract_repo_overview",
                "description": "Extract structured info from a GitHub repository README.",
                "parameters": RepoOverview.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_repo_overview function with the extracted info."},
                {"role": "user", "content": readme_content},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next(item for item in response.output if item.type == "function_call")
        result = RepoOverview.model_validate_json(tool_call.arguments)
        rich.print(result)
    else:
        response = client.responses.parse(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": readme_content},
            ],
            text_format=RepoOverview,
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
        messages=[{"role": "user", "content": readme_content}],
        output_format=RepoOverview,
    )
    rich.print(response.parsed_output)
