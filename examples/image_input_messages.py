import base64
import mimetypes
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_ANTHROPIC_API_KEY"]

# === Choose a model (comment/uncomment) ===
MODEL = os.environ.get("FOUNDRY_ANTHROPIC_DEPLOYMENT", "claude-sonnet-4-5")
# MODEL = "claude-opus-4-5"
# MODEL = "claude-haiku-4-5"

EXAMPLES = [
    ("Is this a unicorn?", "examples/image_aurochs.jpg"),
    ("Are these alligators or crocodiles?", "examples/image_crocodile.png"),
    ("What's the cheapest plant?", "examples/image_plantpage.png"),
]


def open_image_as_base64(filename):
    with open(filename, "rb") as image_file:
        image_data = image_file.read()
    return base64.b64encode(image_data).decode("utf-8")


def guess_media_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "image/png"


client = Anthropic(
    api_key=api_key,
    base_url=endpoint,
)

# Note: URL-based image sources ("type": "url") do not work on Foundry —
# returns "Unable to download the file" error. Use base64 instead.
for prompt, filename in EXAMPLES:
    media_type = guess_media_type(filename)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": open_image_as_base64(filename),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    print(f"=== {prompt} ({filename}) ===")
    print(message.content[0].text)
    print()
