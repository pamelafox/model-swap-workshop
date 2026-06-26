"""ASSERT callable target — workshop travel planner, provider-aware.

The workshop's travel-planner agents are OpenAI-endpoint only, so to compare
models across providers (e.g. gpt-5.5 vs Claude) on the *same* agent we rebuild
the planner on **pydantic-ai** — the framework Pamela already uses for her
cross-provider examples — reusing her *exact* tools and system prompt. Only the
model client changes, so a model swap is a true apples-to-apples comparison.

Select the model under test with ``WORKSHOP_TARGET_MODEL`` (default ``gpt-5.5``).
Names starting with ``claude`` route to the Foundry Anthropic endpoint with
extended thinking ("reasoning") enabled; everything else routes to the Foundry
OpenAI-compatible endpoint.

Env (loaded from .env by the workshop):
  FOUNDRY_MODELS_ENDPOINT, FOUNDRY_API_KEY                      # OpenAI-family models
  FOUNDRY_ANTHROPIC_MODELS_ENDPOINT, FOUNDRY_ANTHROPIC_API_KEY  # Claude models
"""

from __future__ import annotations

import importlib.util
import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

# Best-effort trace capture for the ASSERT judge. ASSERT's auto_trace installs
# OpenInference instrumentors and lets ASSERT's collector capture spans; pydantic-ai
# also emits OTel gen_ai.* spans (instrument=True) that ASSERT maps to tool calls.
# Opt-in via WORKSHOP_TRACE=1 so the default path stays clean with no collector.
_TRACE = os.environ.get("WORKSHOP_TRACE") == "1"
if _TRACE:
    try:
        from assert_ai import auto_trace

        auto_trace.enable()
    except Exception:  # pragma: no cover - tracing is optional
        _TRACE = False

from pydantic_ai import Agent  # noqa: E402

# Reuse Pamela's exact tool implementations from her pydantic-ai trip planner.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PLANNER_PATH = _REPO_ROOT / "examples" / "agent_trip_planner_pydanticai.py"
_spec = importlib.util.spec_from_file_location("_workshop_pydanticai", _PLANNER_PATH)
_planner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_planner)

_TOOLS = [
    _planner.search_flights,
    _planner.search_hotels,
    _planner.check_budget,
    _planner.search_activities,
]

# Pamela's exact system prompt (identical across her trip-planner variants).
_SYSTEM_PROMPT = (
    "You are a travel planning assistant. Help users find flights and hotels within their budget. "
    "IMPORTANT RULES:\n"
    "1. Always search for both flights AND hotels before making a recommendation.\n"
    "2. Prefer direct flights over connecting flights when the price difference is less than $100.\n"
    "3. Always call check_budget before giving your final recommendation to verify it fits.\n"
    "4. If nothing fits the budget, say so clearly — do NOT recommend options that exceed the budget.\n"
    "5. If the user asks for activity suggestions, use search_activities with the remaining budget after flight+hotel."
)

_TARGET_MODEL = os.environ.get("WORKSHOP_TARGET_MODEL", "gpt-5.5")


def _build_model(name: str):
    """Construct a pydantic-ai model client for the named Foundry deployment."""
    if name.lower().startswith("claude"):
        from anthropic import AsyncAnthropic
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        client = AsyncAnthropic(
            base_url=os.environ["FOUNDRY_ANTHROPIC_MODELS_ENDPOINT"] + "/anthropic",
            api_key=os.environ["FOUNDRY_ANTHROPIC_API_KEY"],
        )
        return AnthropicModel(name, provider=AnthropicProvider(anthropic_client=client))

    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    client = AsyncOpenAI(
        base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1",
        api_key=os.environ["FOUNDRY_API_KEY"],
    )
    return OpenAIChatModel(name, provider=OpenAIProvider(openai_client=client))


def _build_agent(name: str) -> Agent:
    kwargs = {}
    if name.lower().startswith("claude"):
        # "reasoning medium": extended thinking with a moderate budget.
        # max_tokens must exceed the thinking budget.
        from pydantic_ai.models.anthropic import AnthropicModelSettings

        kwargs["model_settings"] = AnthropicModelSettings(
            max_tokens=8000,
            anthropic_thinking={"type": "enabled", "budget_tokens": 4096},
        )
    return Agent(
        _build_model(name),
        system_prompt=_SYSTEM_PROMPT,
        tools=_TOOLS,
        instrument=_TRACE,
        **kwargs,
    )


_agent = _build_agent(_TARGET_MODEL)


def chat_sync(message: str, history: list[dict[str, str]] | None = None) -> str:
    """Run one travel-planning turn and return the agent's final text."""
    if history:
        prior = "\n".join(
            f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in history
        )
        prompt = f"{prior}\nuser: {message}"
    else:
        prompt = message
    return _agent.run_sync(prompt).output
