import base64
import mimetypes
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_type = os.environ.get("API_TYPE", "openai_chat_completions")

EXAMPLES = [
    ("Is this a unicorn?", "examples/image_aurochs.jpg"),
    ("Are these alligators or crocodiles?", "examples/image_crocodile.png"),
    ("Is there anything good for vegans on this menu?", "examples/image_menu.png"),
    ("What's the cheapest plant?", "examples/image_plantpage.png"),
]


def open_image_as_base64(filename):
    with open(filename, "rb") as image_file:
        image_data = image_file.read()
    return base64.b64encode(image_data).decode("utf-8")


def guess_media_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "image/png"


if api_type == "openai_chat_completions":
    endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
    # Supported models: gpt-5.5, Mistral-Large-3
    deployment_name = os.environ["FOUNDRY_OPENAI_DEPLOYMENT"]
    api_key = os.environ["FOUNDRY_API_KEY"]

    client = OpenAI(
        base_url=endpoint,
        api_key=api_key,
    )

    for prompt, filename in EXAMPLES:
        media_type = guess_media_type(filename)
        data_uri = f"data:{media_type};base64,{open_image_as_base64(filename)}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ]
        response = client.chat.completions.create(model=deployment_name, messages=messages)
        print(f"=== {prompt} ({filename}) ===")
        print(response.choices[0].message.content)
        print()

elif api_type == "anthropic_messages":
    endpoint = os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic"
    api_key = os.environ["FOUNDRY_ANTHROPIC_API_KEY"]
    # === Choose a model (comment/uncomment) ===
    deployment_name = os.environ.get("FOUNDRY_ANTHROPIC_DEPLOYMENT", "claude-sonnet-4-5")
    # deployment_name = "claude-opus-4-5"
    # deployment_name = "claude-haiku-4-5"

    client = Anthropic(
        api_key=api_key,
        base_url=endpoint,
    )

    # Note: URL-based image sources ("type": "url") do not work on Foundry —
    # returns "Unable to download the file" error. Use base64 instead.
    for prompt, filename in EXAMPLES:
        media_type = guess_media_type(filename)
        message = client.messages.create(
            model=deployment_name,
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