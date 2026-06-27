"""
Agent evaluation: Use azure-ai-evaluation to assess tool calling quality.

Runs our calendar-event tool calling scenario across models, then uses
ToolCallAccuracyEvaluator and TaskAdherenceEvaluator to score whether
models made the right tool calls with correct arguments.

This uses the "simple agent data" format — no Foundry Agent Service or
project required, just the same API key + endpoint.

Usage:
    uv run examples/evals_agent.py
"""

import json
import os

import rich
from azure.ai.evaluation import (
    AzureOpenAIModelConfiguration,
    ToolCallAccuracyEvaluator,
)
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(base_url=endpoint, api_key=api_key)

# Judge model configuration
model_config: AzureOpenAIModelConfiguration = {
    "azure_endpoint": os.environ["FOUNDRY_MODELS_ENDPOINT"].removesuffix("/openai/v1"),
    "azure_deployment": os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", "gpt-5.5"),
    "api_key": api_key,
}

MODELS = [
    "gpt-5.5",
    "Kimi-K2.6",
    "Mistral-Large-3",
    "DeepSeek-V4-Flash",
]

# ---------------------------------------------------------------------------
# Tool definitions (same as function_calling.py)
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "create_calendar_event",
        "description": "Create a calendar event.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title in Title Case (e.g. 'Weekly Standup', 'Q3 Planning')",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format with timezone offset (e.g. 2026-07-01T14:00:00-07:00)",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO 8601 format with timezone offset (e.g. 2026-07-01T15:00:00-07:00)",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone identifier (e.g. 'America/Los_Angeles', 'America/New_York')",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee names only",
                },
                "location": {
                    "type": "string",
                    "description": "Room name, or 'Virtual' for online meetings",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the meeting in minutes",
                },
            },
            "required": ["title", "start_time", "end_time", "timezone"],
            "additionalProperties": False,
        },
    },
]

SYSTEM_PROMPT = "You are a helpful calendar assistant. Today is Monday, June 29, 2026. Use the available tools to process the user's request."
USER_QUERY = "Can you throw something on my calendar? Platform team sync — me, Sarah from eng, Marcus, and that new PM Priya. Tomorrow at 1:30 PT for a half hour. It's virtual, on Microsoft Teams."

# OpenAI Responses API tool format
TOOLS_FOR_API = [
    {"type": "function", "name": t["name"], "description": t["description"], "parameters": t["parameters"]}
    for t in TOOL_DEFINITIONS
]


# ---------------------------------------------------------------------------
# Run tool calling for each model and collect results
# ---------------------------------------------------------------------------
def run_tool_calling(model: str) -> dict:
    """Run the tool calling scenario and return the tool calls + response."""
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_QUERY},
        ],
        tools=TOOLS_FOR_API,
        store=False,
    )

    # Extract tool calls in the format expected by ToolCallAccuracyEvaluator
    tool_calls = []
    text_response = ""
    for item in response.output:
        if item.type == "function_call":
            tool_calls.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments),
            })
        elif item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_response = content.text

    return {"tool_calls": tool_calls, "text_response": text_response}


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------
def main():
    tool_call_eval = ToolCallAccuracyEvaluator(model_config, is_reasoning_model=True)

    print("Running agent evals across models...")
    print(f"Judge model: {model_config['azure_deployment']}")
    print(f"Query: {USER_QUERY}")
    print()

    results = []
    for model in MODELS:
        print(f"  Running {model}...")
        try:
            output = run_tool_calling(model)

            # Build query in message format so the evaluator sees the system prompt context
            query_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [{"type": "text", "text": USER_QUERY}]},
            ]

            # ToolCallAccuracyEvaluator: Did the model call the right tool with right args?
            tca_result = {}
            if output["tool_calls"]:
                tca_result = tool_call_eval(
                    query=query_messages,
                    tool_calls=output["tool_calls"],
                    tool_definitions=TOOL_DEFINITIONS,
                )

            results.append({
                "model": model,
                "tool_calls": output["tool_calls"],
                "text_response": output["text_response"],
                "tool_call_accuracy": tca_result.get("tool_call_accuracy"),
                "tool_call_accuracy_result": tca_result.get("tool_call_accuracy_result"),
            })
        except Exception as e:
            results.append({"model": model, "error": str(e)})
            print(f"    ERROR: {e}")

    # Print results
    print("\n" + "=" * 70)
    print("  AGENT EVALUATION RESULTS (ToolCallAccuracyEvaluator)")
    print("=" * 70)
    print(f"\n  {'Model':<20} {'Score':<10} {'Result':<8} {'Arguments'}")
    print(f"  {'-'*20} {'-'*10} {'-'*8} {'-'*35}")

    for r in results:
        if "error" in r:
            print(f"  {r['model']:<20} {'ERR':<10} {'error':<8} {r['error'][:35]}")
            continue

        tca_score = r.get("tool_call_accuracy")

        if r["tool_calls"]:
            args = r["tool_calls"][0]["arguments"]
            attendees = args.get("attendees", [])
            location = args.get("location", "")
            args_str = (
                f"attendees={attendees}, "
                f"location={location}"
            )
            result_str = r.get("tool_call_accuracy_result", "N/A")
            score_str = f"{tca_score}/5" if tca_score is not None else "N/A"
        else:
            args_str = f"(asked: {r['text_response'][:35]}...)" if r["text_response"] else "(no action)"
            result_str = "N/A"
            score_str = "N/A"

        print(f"  {r['model']:<20} {score_str:<10} {result_str:<8} {args_str}")

    print("\n  Scoring: 5=perfect tool call, 3=threshold, 1-2=wrong tool/args")
    print("  Expected: attendees=['Sarah','Marcus','Priya'], location='Virtual'")


if __name__ == "__main__":
    main()
