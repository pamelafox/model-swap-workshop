"""
Tool loop: Multi-step math with a calculator tool.

Tests whether models correctly decompose a word problem into sequential
tool calls, or try to cram everything into one expression.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
# MODEL = "Mistral-Large-3"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(base_url=endpoint, api_key=api_key)

tools = [
    {
        "type": "function",
        "name": "calculate",
        "description": "Evaluate a single arithmetic expression and return the numeric result. Only supports basic math: +, -, *, /, **, parentheses.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A single arithmetic expression, e.g. '(15 * 3) + 7'",
                },
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
]


def calculate(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
        # Only allow safe math operations
        allowed = set("0123456789+-*/.(). ")
        if not all(c in allowed or c == "*" for c in expression):
            return "Error: unsafe expression"
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


USER_MESSAGE = (
    "A store is having a sale: all shirts are 30% off their original price of $45, "
    "and there's an additional 10% loyalty discount applied after the sale price. "
    "If I buy 3 shirts and pay 8.5% sales tax on the final amount, "
    "what's my total?"
)
# Expected steps: 45*0.7=31.5, 31.5*0.9=28.35, 28.35*3=85.05, 85.05*1.085=92.28
# Expected answer: ~$92.28

print(f"User: {USER_MESSAGE}\n")

messages = [
    {"role": "system", "content": "Do not do math in your head."},
    {"role": "user", "content": USER_MESSAGE},
]

total_tool_calls = 0
while True:
    response = client.responses.create(
        model=deployment_name,
        input=messages,
        tools=tools,
        store=False,
    )

    tool_calls = [item for item in response.output if item.type == "function_call"]

    if not tool_calls:
        print(f"Assistant: {response.output_text}")
        print(f"\n(Total tool calls: {total_tool_calls})")
        break

    total_tool_calls += len(tool_calls)

    for item in response.output:
        item_dict = item.model_dump(exclude_none=True)
        item_dict.pop("id", None)
        messages.append(item_dict)

    for tool_call in tool_calls:
        args = json.loads(tool_call.arguments)
        expr = args["expression"]
        result = calculate(expr)
        print(f"  [calculate] {expr} = {result}")

        messages.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": result,
            }
        )

    print()
