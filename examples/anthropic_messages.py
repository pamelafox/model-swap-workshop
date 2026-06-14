import os

from anthropic import Anthropic
from anthropic.lib.credentials import AccessToken
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv

load_dotenv(override=True)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic"
deployment_name = os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"]

def _entra_credentials_provider(scope: str = "https://ai.azure.com/.default"):
    """Build an Anthropic `AccessTokenProvider` backed by `AzureDeveloperCliCredential`.

    The provider is called by the SDK's `TokenCache` only when there is no
    cached token, when the cached token has expired, or when a 401 forced an
    invalidation. `azure.identity` itself also caches and refreshes tokens
    internally, so this stays cheap on the hot path.
    """
    credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])

    def _provider(*, force_refresh: bool = False) -> AccessToken:
        # `force_refresh` is set by TokenCache.invalidate() after a 401.
        # AzureDeveloperCliCredential does not expose a force-refresh knob, but
        # re-calling get_token() is enough: it will mint a new token if the
        # cached one is close to expiry, which is the common 401 cause.
        token = credential.get_token(scope)
        # `expires_on` is unix seconds — the format Anthropic's TokenCache expects.
        return AccessToken(token=token.token, expires_at=token.expires_on)

    return _provider

client = Anthropic(
    credentials=_entra_credentials_provider(),
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