import base64
import mimetypes
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

# === Choose a model (comment/uncomment) ===
MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "Mistral-Large-3"

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
    response = client.chat.completions.create(model=MODEL, messages=messages)
    print(f"=== {prompt} ({filename}) ===")
    print(response.choices[0].message.content)
    print()