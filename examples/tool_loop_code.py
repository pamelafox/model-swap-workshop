# /// script
# dependencies = ["pydantic-monty>=0.0.18", "openai>=1.0", "python-dotenv"]
# ///
import json
import os

import pydantic_monty
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
#MODEL = "DeepSeek-V4-Flash"
#MODEL = "Mistral-Large-3"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

tools = [
    {
        "type": "function",
        "name": "execute_python",
        "description": "Execute a Python code snippet and return the result. Use this for any date/time calculations, math, or logic that requires precise computation.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. The last expression's value will be returned as the result.",
                },
            },
            "required": ["code"],
            "additionalProperties": False,
        },
    },
]


def execute_code(code: str) -> str:
    """Execute Python code using Monty sandbox and return the result."""
    try:
        monty = pydantic_monty.Monty(code)
        result = monty.run()
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


USER_MESSAGE = (
    'How many times does the letter "e" appear in the following sentence? '
    "Count carefully.\n"
    '"The elderly gentleman eagerly entered the elevator."'
)

print(f"User: {USER_MESSAGE}\n")

messages = [
    {"role": "system", "content": "You are a helpful assistant. Use the execute_python tool for any counting or calculations instead of trying to compute them yourself."},
    {"role": "user", "content": USER_MESSAGE},
]

# Agent loop: keep calling the model until we get a final text response
total_tool_calls = 0
while True:
    response = client.responses.create(
        model=deployment_name,
        input=messages,
        tools=tools,
        # -- Experiment with these parameters to affect the output:
        # -- temperature is not supported on gpt-5 models, but works on others
        # temperature=0.3,
        # -- reasoning is only supported on gpt-5 models, but not others
        # reasoning={"effort": "medium", "summary": "detailed"},
        store=False,
    )

    tool_calls = [item for item in response.output if item.type == "function_call"]

    if not tool_calls:
        print(f"Assistant: {response.output_text}")
        print(f"\n(Total tool calls: {total_tool_calls})")
        break

    total_tool_calls += len(tool_calls)

    # Process tool calls and feed results back
    for item in response.output:
        item_dict = item.model_dump(exclude_none=True)
        item_dict.pop("id", None)
        messages.append(item_dict)

    for tool_call in tool_calls:
        args = json.loads(tool_call.arguments)
        code = args["code"]
        print("[Tool call] execute_python:")
        print(f"  {code}")
        result = execute_code(code)
        print(f"[Result] {result}\n")

        messages.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": result,
            }
        )
