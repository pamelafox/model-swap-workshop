"""
Tool calling: Calendar event creation / format normalization.

Tests whether models can parse a casual meeting description into structured fields.
Models differ on: whether "me" is included in attendees, how location is
normalized when the schema says 'Virtual', and attendee name cleanup.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.table import Table

load_dotenv()

MODEL = "gpt-5.5"
# MODEL = "Kimi-K2.6"
# MODEL = "DeepSeek-V4-Flash"
# MODEL = "Mistral-Large-3"
deployment_name = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", MODEL)

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(
    base_url=endpoint,
    api_key=api_key,
)

tools = [
    {
        "type": "function",
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

USER_MESSAGE = (
    "Can you throw something on my calendar? Platform team sync — "
    "me, Sarah from eng, Marcus, and that new PM Priya. "
    "Tomorrow at 1:30 PT for a half hour. It's virtual, on Microsoft Teams."
)

response = client.responses.create(
    model=deployment_name,
    input=[
        {"role": "system", "content": "You are a helpful calendar assistant. Today is Monday, June 29, 2026. Use the available tools to process the user's request."},
        {"role": "user", "content": USER_MESSAGE},
    ],
    tools=tools,
    store=False,
)

print(f"Response from {deployment_name}:\n")
tool_calls = [item for item in response.output if item.type == "function_call"]
tool_arguments= {}
if tool_calls:
    tool_arguments = json.loads(tool_calls[0].arguments)
else:
    print(response.output_text)

expected = {
    "title": "Platform Team Sync",
    "start_time": "2026-06-30T13:30:00-07:00",
    "end_time": "2026-06-30T14:00:00-07:00",
    "timezone": "America/Los_Angeles",
    "attendees": ["Sarah", "Marcus", "Priya"],
    "location": "Virtual",
    "duration_minutes": 30,
}
if tool_arguments:
    table = Table(title=f"Tool call: {tool_calls[0].name}")
    table.add_column("", style="bold")
    table.add_column("Field")
    table.add_column("Expected")
    table.add_column("Actual")
    for key in expected:
        actual_val = tool_arguments.get(key, "—")
        expected_val = expected[key]
        match = "✅" if actual_val == expected_val else "❌"
        table.add_row(match, key, str(expected_val), str(actual_val))
    Console().print(table)
