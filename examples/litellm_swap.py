import os
import logging

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from litellm import completion
import litellm

#litellm._turn_on_debug()
#logging.basicConfig(level=logging.DEBUG)

load_dotenv(override=True)

azure_token_provider = get_bearer_token_provider(
    AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"]),
    "https://ai.azure.com/.default",
)

provider = os.environ.get("MODEL_CHOICE", "openai")
if provider == "openai":
    model = f"azure/responses/{os.environ['FOUNDRY_OPENAI_DEPLOYMENT']}"
    api_base = os.environ["FOUNDRY_MODELS_ENDPOINT"]
    kwargs = {}
elif provider == "claude":
    model = f"azure_ai/{os.environ['FOUNDRY_CLAUDE_DEPLOYMENT']}"
    api_base = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic"
    kwargs = {"thinking": {"type": "enabled", "budget_tokens": 1024}}

response = completion(
    model=model,
    api_base=api_base,
    azure_ad_token_provider=azure_token_provider,
    messages=[{"role": "user", "content": "What is the capital of France?"}],
    **kwargs,
)

print(response.choices[0].message.content)
