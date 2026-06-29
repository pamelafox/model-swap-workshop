import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"]

# === Choose a model (comment/uncomment) ===
# MODEL = "claude-opus-4-5"
MODEL = "claude-sonnet-4-5"
# MODEL = "claude-haiku-4-5"

# Env var override for batch testing (manual_test.sh sets this)
deployment_name = os.environ.get("FOUNDRY_ANTHROPIC_DEPLOYMENT", MODEL)

client = Anthropic(
    api_key=os.environ["FOUNDRY_ANTHROPIC_API_KEY"],
    base_url=endpoint,
)


message = client.messages.create(
    model=deployment_name,
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ],
    max_tokens=1024,
)

print(message.content)