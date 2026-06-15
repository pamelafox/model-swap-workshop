import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic"
deployment_name = os.environ["FOUNDRY_ANTHROPIC_CLAUDE_DEPLOYMENT"]

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