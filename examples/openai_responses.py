import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

extra_kwargs = {}
if deployment_name.startswith("gpt-5."):
    # gpt-5 series do not support temperature; use reasoning effort instead
    extra_kwargs["reasoning"] = {
        "effort": "medium",
        "summary": "detailed",  # auto, concise, or detailed, gpt-5 series do not support concise
    }
else:
    extra_kwargs["temperature"] = 0.5

PROMPT = """
Solve this logic puzzle and show your final answer clearly:
Three boxes are labeled APPLES, ORANGES, and MIXED. Every label is wrong.
You may pick exactly one fruit from exactly one box (without looking inside first).
What single box should you pick from, and how can you relabel all three boxes correctly?"
"""

response = client.responses.create(
    model=deployment_name,
    input=(
        "Solve this logic puzzle and show your final answer clearly:\n"
        "\n"
        "Three boxes are labeled APPLES, ORANGES, and MIXED. Every label is wrong. "
        "You may pick exactly one fruit from exactly one box (without looking inside first). "
        "What single box should you pick from, and how can you relabel all three boxes correctly?"
    ),
    **extra_kwargs
)

print(response.model_dump_json(indent=2))