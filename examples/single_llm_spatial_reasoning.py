"""
Single LLM call: Spatial reasoning (rotation tracking).

Tests multi-step state tracking — the model must mentally simulate
sequential rotations and report the final compass direction.

What to observe:
- Correct answer: Southeast (N -> E -> S -> left 45° -> SE)
- Reasoning models track state correctly
- Others often get the left-turn direction wrong (NE) or confuse themselves

Usage:
    uv run examples/single_llm_spatial_reasoning.py
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# === Choose a model (comment/uncomment) ===
MODEL = "gpt-5.5"
# MODEL = "Mistral-Large-3"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"

# Env var override for batch testing (manual_test.sh sets this)
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)


client = OpenAI(
    base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1",
    api_key=os.environ["FOUNDRY_API_KEY"],
)

PROMPT = (
    "I am standing in the center of a room facing north. "
    "I turn right 90 degrees. I turn right 90 degrees again. "
    "I turn left 45 degrees. "
    "What compass direction am I now facing? "
    "Answer with just the direction and a one-sentence explanation."
)

response = client.responses.create(
    model=deployment_name,
    input=PROMPT,
    # -- Experiment with these parameters to affect the output:
    # -- temperature is not supported on gpt-5 models, but works on others
    # temperature=0.3,
    # -- reasoning is only supported on gpt-5 models, but not others
    # reasoning={"effort": "medium", "summary": "detailed"},
)

# Extract text (handles Kimi's reasoning prefix)
text = ""
for item in response.output:
    if item.type == "message":
        for content in item.content:
            if content.type == "output_text":
                text = content.text

print(f"Model: {deployment_name}")
print(f"Prompt: {PROMPT}")
print(f"\nResponse: {text}")
print("\n(Correct answer: Southeast)")
