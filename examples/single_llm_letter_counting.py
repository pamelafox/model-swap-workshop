"""
Single LLM call: Letter counting.

Tests character-level awareness — models must count individual letters
in a sentence, which requires reasoning about tokenization boundaries.

What to observe:
- Reasoning models (gpt-5.5, Kimi) tend to get this right (answer: 13)
- Non-reasoning models often undercount significantly

Usage:
    uv run examples/single_llm_letter_counting.py
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
    'How many times does the letter "e" appear in the following sentence? '
    "Count carefully.\n"
    '"The elderly gentleman eagerly entered the elevator."\n'
    "Give just the number."
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
print("\n(Correct answer: 13)")
