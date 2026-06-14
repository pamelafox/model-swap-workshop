import os

from openai import OpenAI
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv(override=True)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]
azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
token_provider = get_bearer_token_provider(azure_credential, "https://ai.azure.com/.default")

client = OpenAI(
    base_url=endpoint,
    api_key=token_provider
)

response = client.responses.create(
    model=deployment_name,
    input="What is the capital of France?",
)

print(response.output[0])
