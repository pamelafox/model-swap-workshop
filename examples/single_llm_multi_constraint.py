"""
Single LLM call: Multi-constraint satisfaction.

Tests juggling three simultaneous constraints:
1. Acrostic: first letters must spell "FIT"
2. Word count: each line must be exactly 6 words
3. Format: numbered list, nothing else

What to observe:
- Strong models nail all three constraints
- Weaker models tend to sacrifice word count to preserve the acrostic
- Some models add extra text despite "nothing else" instruction

Usage:
    uv run examples/single_llm_multi_constraint.py
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# === Choose a model (comment/uncomment) ===
MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
# MODEL = "Mistral-Large-3"

# Env var override for batch testing (manual_test.sh sets this)
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)


client = OpenAI(
    base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"],
    api_key=os.environ["FOUNDRY_API_KEY"],
)

PROMPT = (
    "List exactly 3 benefits of exercise. "
    "Each benefit must be stated in exactly 6 words. "
    "The first letter of each benefit must spell out the word 'FIT' (F, I, T). "
    "Output only the 3 benefits as a numbered list, nothing else."
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
print(f"\nResponse:\n{text}")

# Quick validation
lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
print("\n--- Validation ---")
for i, line in enumerate(lines):
    # Strip numbering prefix like "1. " or "1) "
    content = line.lstrip("0123456789.)- ").strip()
    words = content.split()
    first_letter = content[0] if content else "?"
    print(f"  Line {i+1}: {len(words)} words, starts with '{first_letter}' | {content}")
