"""
Basic evaluations: Programmatic checks on tool calling across models.

Tests 5 edge cases for calendar event creation via tool calling:
1. Standard meeting with attendee normalization and timezone handling
2. Multi-day event with date math (recurring weekly)
3. Ambiguous duration ("quick chat" = 15 min)
4. Request in Spanish — model must still produce correct tool args
5. Conflicting signals — informal language with formal event type

No eval framework needed — just programmatic checks on the tool call arguments.

Usage:
    uv run examples/evals_basic.py
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(base_url=endpoint, api_key=api_key)

MODELS = [
    "gpt-5.5",
    "Kimi-K2.6",
    "Mistral-Large-3",
    "DeepSeek-V4-Flash",
]

CALENDAR_TOOL = {
    "type": "function",
    "name": "create_calendar_event",
    "description": "Create a calendar event.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title in Title Case (e.g. 'Weekly Standup', 'Q3 Planning')"},
            "start_time": {"type": "string", "description": "Start time in ISO 8601 format with timezone offset (e.g. 2026-07-01T14:00:00-07:00)"},
            "end_time": {"type": "string", "description": "End time in ISO 8601 format with timezone offset (e.g. 2026-07-01T15:00:00-07:00)"},
            "timezone": {"type": "string", "description": "IANA timezone identifier (e.g. 'America/Los_Angeles', 'America/New_York')"},
            "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee names only (not 'me' or the user)"},
            "location": {"type": "string", "description": "Room name, or 'Virtual' for online meetings"},
            "duration_minutes": {"type": "integer", "description": "Duration of the meeting in minutes"},
        },
        "required": ["title", "start_time", "end_time", "timezone"],
        "additionalProperties": False,
    },
}

SYSTEM_PROMPT = "You are a helpful calendar assistant. Today is Monday, June 29, 2026. Use the available tools to process the user's request."


# ---------------------------------------------------------------------------
# Helper: call model and extract tool call arguments
# ---------------------------------------------------------------------------
def get_tool_args(model: str, user_message: str) -> dict | None:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        tools=[CALENDAR_TOOL],
        store=False,
    )
    tool_call = next((item for item in response.output if item.type == "function_call"), None)
    if tool_call:
        return json.loads(tool_call.arguments)
    return None


# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "name": "attendee_normalization",
        "description": "Standard meeting — exclude 'me' from attendees, normalize location to 'Virtual'",
        "user_message": (
            "Can you throw something on my calendar? Platform team sync — "
            "me, Sarah from eng, Marcus, and that new PM Priya. "
            "Tomorrow at 1:30 PT for a half hour. It's virtual, on Microsoft Teams."
        ),
        "checks": lambda args: {
            "no_me_in_attendees": not any(a.lower() in ("me", "you") for a in args.get("attendees", [])),
            "has_sarah": any("sarah" in a.lower() for a in args.get("attendees", [])),
            "has_marcus": any("marcus" in a.lower() for a in args.get("attendees", [])),
            "has_priya": any("priya" in a.lower() for a in args.get("attendees", [])),
            "location_virtual": args.get("location") == "Virtual",
            "start_time_correct": args.get("start_time", "").startswith("2026-06-30T13:30"),
            "duration_30": args.get("duration_minutes") == 30,
        },
    },
    {
        "name": "date_math_next_week",
        "description": "Date math — 'next Wednesday' should resolve to July 8",
        "user_message": (
            "Schedule a 2-hour planning session next Wednesday at 10am Eastern. "
            "Title it 'Q3 Roadmap Planning'. Invite Dev, Anita, and Jorge. "
            "We'll be in Conference Room B."
        ),
        "checks": lambda args: {
            "title_correct": args.get("title", "").lower().replace(" ", "") == "q3roadmapplanning"
                or "q3" in args.get("title", "").lower() and "planning" in args.get("title", "").lower(),
            "date_is_july_8_or_9": args.get("start_time", "").startswith("2026-07-08T10:00")
                or args.get("start_time", "").startswith("2026-07-09T10:00"),
            "timezone_eastern": "New_York" in args.get("timezone", "") or "Eastern" in args.get("timezone", ""),
            "duration_120": args.get("duration_minutes") == 120
                or (args.get("end_time", "").startswith("2026-07-08T12:00") or args.get("end_time", "").startswith("2026-07-09T12:00")),
            "location_room_b": "b" in args.get("location", "").lower(),
        },
    },
    {
        "name": "ambiguous_duration",
        "description": "Ambiguous duration — 'quick chat' with no explicit time should default to 15 min",
        "user_message": (
            "I need a quick chat with Tomoko tomorrow at 3pm Pacific. "
            "Just a virtual check-in, nothing formal."
        ),
        "checks": lambda args: {
            "has_tomoko": any("tomoko" in a.lower() for a in args.get("attendees", [])),
            "short_duration": args.get("duration_minutes", 60) <= 30,
            "start_time_3pm": "T15:00" in args.get("start_time", ""),
            "location_virtual": args.get("location", "").lower() == "virtual",
            "date_tomorrow": args.get("start_time", "").startswith("2026-06-30"),
        },
    },
    {
        "name": "spanish_request",
        "description": "Spanish input — model must parse correctly despite non-English",
        "user_message": (
            "Agenda una reunión para el viernes a las 4 de la tarde, hora de Ciudad de México. "
            "Invita a Carlos y a María. Será en la Sala Juárez, una hora. "
            "Ponle 'Revisión de Presupuesto'."
        ),
        "checks": lambda args: {
            "title_spanish": "presupuesto" in args.get("title", "").lower() or "revision" in args.get("title", "").lower().replace("ó", "o"),
            "date_friday_july_3": args.get("start_time", "").startswith("2026-07-03T16:00")
                or args.get("start_time", "").startswith("2026-07-04T16:00"),
            "timezone_mexico": "Mexico" in args.get("timezone", ""),
            "has_carlos": any("carlos" in a.lower() for a in args.get("attendees", [])),
            "has_maria": any("mar" in a.lower() for a in args.get("attendees", [])),
            "duration_60": args.get("duration_minutes") == 60
                or "T17:00" in args.get("end_time", ""),
        },
    },
    {
        "name": "formal_from_informal",
        "description": "Informal language but formal event — title should still be professional",
        "user_message": (
            "yo can u book the big conf room (Auditorium A) for this Thursday from 9 to 11am PT? "
            "it's the all-hands meeting. whole engineering dept is invited but just put "
            "Li Wei, Fatima, and Raj as required attendees."
        ),
        "checks": lambda args: {
            "title_professional": "all" in args.get("title", "").lower() and "hands" in args.get("title", "").lower(),
            "date_thursday_july_2": args.get("start_time", "").startswith("2026-07-02T09:00")
                or args.get("start_time", "").startswith("2026-07-03T09:00"),
            "end_time_11am": "T11:00" in args.get("end_time", ""),
            "location_auditorium": "auditorium" in args.get("location", "").lower(),
            "has_required_attendees": (
                any("li" in a.lower() for a in args.get("attendees", []))
                and any("fatima" in a.lower() for a in args.get("attendees", []))
                and any("raj" in a.lower() for a in args.get("attendees", []))
            ),
            "duration_120": args.get("duration_minutes") == 120
                or "T11:00" in args.get("end_time", ""),
        },
    },
]


# ---------------------------------------------------------------------------
# Run all evals
# ---------------------------------------------------------------------------
def main():
    print("Evaluating tool calling across models")
    print(f"{'='*60}")

    results = []
    for model in MODELS:
        print(f"\n  {model}:")
        for case in TEST_CASES:
            try:
                args = get_tool_args(model, case["user_message"])
                if args is None:
                    result = {"name": case["name"], "model": model, "pass": False, "actual": "NO_TOOL_CALL", "checks": {}}
                else:
                    checks = case["checks"](args)
                    all_pass = all(checks.values())
                    result = {"name": case["name"], "model": model, "pass": all_pass, "actual": args, "checks": checks}
                results.append(result)
                status = "✅ PASS" if result["pass"] else "❌ FAIL"
                failed_checks = [k for k, v in result.get("checks", {}).items() if not v]
                extra = f"  failed: {failed_checks}" if failed_checks else ""
                print(f"    {status}  {case['name']:25s}{extra}")
            except Exception as e:
                results.append({"name": case["name"], "model": model, "pass": False, "error": str(e)})
                print(f"    💥 ERROR {case['name']}: {e}")

    # Summary table
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Model':<20} {'Passed':<8} {'Failed':<8} {'Score'}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8}")
    for model in MODELS:
        model_results = [r for r in results if r["model"] == model]
        passed = sum(1 for r in model_results if r.get("pass"))
        failed = len(model_results) - passed
        print(f"  {model:<20} {passed:<8} {failed:<8} {passed}/{len(model_results)}")


if __name__ == "__main__":
    main()
