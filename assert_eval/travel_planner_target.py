"""ASSERT callable target — wraps Pamela's LangChain travel planner.

ASSERT calls ``chat_sync(message, history)`` once per generated test case. We
import ``examples/agent_trip_planner_langchain.py`` *unchanged* and (with
``WORKSHOP_TRACE=1``) turn on ASSERT's auto-tracing first, so the LangChain
OpenInference instrumentor captures every tool call and routing decision and
ASSERT's judge can cite them as evidence — not just the final text.

Model swap: the underlying agent reads ``FOUNDRY_OPENAI_DEPLOYMENT`` at import
time. Set ``WORKSHOP_TARGET_MODEL`` (preferred) or ``FOUNDRY_OPENAI_DEPLOYMENT``
before running ``assert-ai run`` to evaluate a different model. The ASSERT
pipeline (generation + judge) is configured separately in
``travel_planner_eval.yaml`` and stays fixed across swaps.

Env (loaded from .env by the workshop):
  FOUNDRY_MODELS_ENDPOINT, FOUNDRY_API_KEY    # the OpenAI-compatible Foundry endpoint
"""

from __future__ import annotations

import importlib.util
import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

# Pick the model under test and expose it to the agent module (which reads
# FOUNDRY_OPENAI_DEPLOYMENT at import time) BEFORE importing it below.
_TARGET_MODEL = os.environ.get("WORKSHOP_TARGET_MODEL")
if _TARGET_MODEL:
    os.environ["FOUNDRY_OPENAI_DEPLOYMENT"] = _TARGET_MODEL

# Enable trace capture BEFORE importing the agent so the LangChain OpenInference
# instrumentor patches it. ASSERT's in-process collector captures the emitted
# spans during the run — no Phoenix server required. Opt-in via WORKSHOP_TRACE=1.
_TRACE = os.environ.get("WORKSHOP_TRACE") == "1"
if _TRACE:
    try:
        from assert_ai import auto_trace

        auto_trace.enable()
    except Exception:  # pragma: no cover - tracing is optional
        _TRACE = False

# Import Pamela's LangChain travel planner unchanged.
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
