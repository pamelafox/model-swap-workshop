import os
import warnings

# Must be set before importing openai/pydantic to avoid MockValSer crash.
# See: https://github.com/openai/openai-python/issues/1306
os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")

import requests
import rich
from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)

api_type = os.environ.get("API_TYPE", "openai_responses")


# Define models for Structured Outputs
class BlogPost(BaseModel):
    title: str
    summary: str = Field(..., description="A 1-2 sentence summary of the blog post")
    tags: list[str] = Field(..., description="A list of tags for the blog post, like 'python' or 'openai'")


SYSTEM_PROMPT = "Extract the information from the blog post"

# Fetch blog post and extract title/content
url = "https://blog.pamelafox.org/2024/09/integrating-vision-into-rag-applications.html"
response = requests.get(url)
if response.status_code != 200:
    print(f"Failed to fetch the page: {response.status_code}")
    exit(1)
soup = BeautifulSoup(response.content, "html.parser")
post_title = soup.find("h3", class_="post-title")
post_contents = soup.find("div", class_="post-body").get_text(strip=True)
user_content = f"{post_title}\n{post_contents}"

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
                "name": "extract_blog_post",
                "description": "Extract structured info from a blog post.",
                "parameters": BlogPost.model_json_schema(),
            }
        ]
        response = client.responses.create(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT + " Call the extract_blog_post function with the extracted info."},
                {"role": "user", "content": user_content},
            ],
            tools=tools,
            tool_choice="required",
            store=False,
        )
        tool_call = next(item for item in response.output if item.type == "function_call")
        result = BlogPost.model_validate_json(tool_call.arguments)
        rich.print(result)
    else:
        response = client.responses.parse(
            model=deployment_name,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            text_format=BlogPost,
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
        messages=[{"role": "user", "content": user_content}],
        output_format=BlogPost,
    )
    rich.print(response.parsed_output)
