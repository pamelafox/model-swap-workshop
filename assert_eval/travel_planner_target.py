"""ASSERT callable target — wraps the existing LangChain travel planner.

ASSERT calls ``chat_sync(message, history)`` once per generated test case. We
load ``examples/agent_trip_planner_langchain.py`` *unchanged* and (optionally)
turn on Phoenix / OpenInference tracing so the ASSERT judge can cite tool calls
and routing as evidence — not just the final text.

Model swap: the underlying agent reads ``FOUNDRY_OPENAI_DEPLOYMENT`` at import
time, so set that env var *before* running ``assert-ai run`` to evaluate a
different model. The ASSERT pipeline (generation + judge) is configured
separately in ``travel_planner_eval.yaml`` and stays fixed across swaps.
"""

from __future__ import annotations

import importlib.util
import pathlib

# Enable trace capture BEFORE importing the agent so the LangChain instrumentor
# patches it. Falls back to a plain (untraced) callable if Phoenix /
# OpenInference is not installed.
try:
    from phoenix.otel import register

    register(auto_instrument=True)
except Exception:  # pragma: no cover - tracing is optional
    pass

# Load the existing agent module by file path (works whether or not
# ``examples`` is an importable package).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PLANNER_PATH = _REPO_ROOT / "examples" / "agent_trip_planner_langchain.py"

_spec = importlib.util.spec_from_file_location(
    "agent_trip_planner_langchain", _PLANNER_PATH
)
_planner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_planner)

_agent = _planner.agent
_logger = _planner.logger


def chat_sync(message: str, history: list[dict[str, str]] | None = None) -> str:
    """Run one travel-planning turn and return the agent's final text.

    ``history`` (passed by ASSERT for multi-turn scenarios) is a list of
    ``{"role": ..., "content": ...}`` messages preceding ``message``.
    """
    _logger.pending_calls = []
    _logger.turn = 0

    messages: list[dict[str, str]] = []
    for turn in history or []:
        messages.append(
            {"role": turn.get("role", "user"), "content": turn.get("content", "")}
        )
    messages.append({"role": "user", "content": message})

    response = _agent.invoke({"messages": messages})
    return response["messages"][-1].text
