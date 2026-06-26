# Scenario-grounded model-swap evals with ASSERT

> **Thesis for this segment:** *Evaluate your model upgrades in the context of **your** scenarios — not generic benchmarks.*

This folder adds an [ASSERT](https://github.com/responsibleai/ASSERT) evaluation on top of the existing **LangChain travel planner** (`examples/agent_trip_planner_langchain.py`). It upgrades the workshop's generic judges (programmatic checks, RAG groundedness, single tool-call accuracy) into a **scenario-grounded judge** that scores the *whole* travel-planning behavior — budget, constraints, tool routing, grounding — and lets you compare models **on the same scenario** as you swap them.

It plugs into your existing flow: keep Parts 1–6 as-is, then make Part 7 (evals) and Part 8 (DSPy) ASSERT-powered.

## What you get

| Generic eval tells you | ASSERT tells you |
|---|---|
| Did the model pass toy/deterministic checks? | Did the planner satisfy generated variants of *your* behavior spec? |
| Was a RAG answer grounded? | Were the travel recommendations grounded in the agent's *own tool outputs*? |
| Did one calendar tool call have the right args? | Did the agent call the right tools in the right **dependency order**? |
| One generic score | A per-dimension regression story: **budget, constraints, routing, groundedness, overrefusal** |

## Files

| File | Role |
|---|---|
| `travel_planner_eval.yaml` | The ASSERT eval: behavior spec → generated test cases → judge dimensions for the travel planner. |
| `travel_planner_target.py` | Thin wrapper exposing your LangChain agent to ASSERT as `chat_sync`, with optional Phoenix/OpenInference tracing. |
| `__init__.py` | Makes `assert_eval` importable so the callable path resolves. |

## Setup

```bash
uv add assert-ai arize-phoenix-otel openinference-instrumentation-langchain
```

ASSERT uses **two** model paths — keep them straight:

| Path | Used by | Env vars |
|---|---|---|
| **Target** (the agent under test) | your existing LangChain agent | `FOUNDRY_MODELS_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_OPENAI_DEPLOYMENT` (unchanged) |
| **Pipeline** (generation + judge) | ASSERT's LiteLLM calls in `travel_planner_eval.yaml` | `AZURE_API_BASE`, `AZURE_API_KEY` |

Point the pipeline at your Foundry account (placeholders — never commit real keys):

```bash
export AZURE_API_BASE="$FOUNDRY_MODELS_ENDPOINT"   # e.g. https://YOUR-ACCOUNT.services.ai.azure.com
export AZURE_AI_API_KEY="$FOUNDRY_API_KEY"         # bearer for azure_ai/* (Foundry) routes
export AZURE_API_KEY="$FOUNDRY_API_KEY"            # fallback
```

The pipeline models use the `azure_ai/*` LiteLLM route (Azure AI Foundry), e.g. `azure_ai/gpt-5.5`. If `gpt-5.5` isn't a deployment you have, change the `name:` values in `travel_planner_eval.yaml` to one you do. The pipeline model stays **fixed** while you swap the target — you don't want to change your judge mid-comparison.

> **Two config gotchas (learned the hard way, both already handled in the bundled config):**
> 1. **Dimensions use explicit `levels`, not `description`.** Stratification's web-search path isn't available on Foundry `azure_ai/*` models, so generated-mode dimensions fail. Explicit `levels` skip that call.
> 2. **`systematize.model.max_tokens` is 16000.** A lower cap truncates the structured taxonomy and yields zero behavior categories.

> **Note:** `temperature` is omitted in the config on purpose — the gpt-5 family only accepts `temperature=1.0` (the provider default when none is sent), so omitting it keeps the config working across model families.

## Run the model-swap loop (the core demo)

Hold the eval spec fixed; change only the **target** model via `FOUNDRY_OPENAI_DEPLOYMENT`:

```bash
# optional: live trace UI
phoenix serve

FOUNDRY_OPENAI_DEPLOYMENT="gpt-5.5"        assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=gpt-55
FOUNDRY_OPENAI_DEPLOYMENT="Kimi-K2.6"      assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=kimi-k26
FOUNDRY_OPENAI_DEPLOYMENT="Mistral-Large-3" assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=mistral-large-3
```

PowerShell:

```powershell
$env:FOUNDRY_OPENAI_DEPLOYMENT = "gpt-5.5"
assert-ai run --config assert_eval\travel_planner_eval.yaml --override run=gpt-55
```

Run `assert-ai run` from the repo root so the `assert_eval.travel_planner_target:chat_sync` callable resolves.

## See it in the viewer (the payoff moment)

```bash
git clone https://github.com/responsibleai/ASSERT
cd ASSERT/viewer && npm install && npm run dev   # http://localhost:5174
```

Point the viewer at this repo's `artifacts/results/` (`ARTIFACTS_ROOT`), open the `pamela-travel-planner-model-swap` suite, and **compare runs by dimension**. Drill into one failed row to show the judge's verdict cited against the captured tool calls.

## Talk beats (drop-in to your existing arc)

| Your beat | ASSERT moment | Why it lands |
|---|---|---|
| Opening premise | "Today the eval stays fixed while the model changes." Show the config as the scenario contract. | Moves from "watch it break" to "measure what broke." |
| Parts 1–5 | Keep as-is — label them capability probes, not app evals. | Sets up the generic-vs-scenario contrast. |
| Part 6 travel agent | Run the planner normally, then run `assert-ai run` against it. | Converts "watch behavior" into "measure behavior." |
| Part 7 evals | Replace/augment the generic judge with the ASSERT travel-planner eval. | The evaluator is derived from *your* scenario spec. |
| **Viewer compare** | `gpt-5.5` vs `Kimi`/`Mistral` per dimension; open one trace-cited failure. | **The main proof of the thesis.** |
| Part 8 DSPy | Use ASSERT scores as the optimization signal; re-run ASSERT after GEPA. | Closes the loop: measure → optimize → re-measure. |
| Recap | "Hold the scenario fixed, swap the model, compare scenario failures, optimize what matters." | Clean takeaway. |

### Lines to say

> "We're not asking whether Kimi beats Mistral on a generic benchmark. We're asking: when *this* travel planner has to stay under budget, prefer direct flights, validate tool results, and suggest an activity with the remaining budget — which model regresses *our* scenario?"

> **The punchline:** a "better" model can still regress on budget validation or tool dependency order — and ASSERT makes that visible, per dimension, on your scenario.

## DSPy finale, closed-loop

Keep your GEPA finale, but swap the objective: instead of the toy `constraint_metric`, optimize against ASSERT's per-dimension scores from `metrics.json` (read e.g. `budget_adherence`, `tool_routing_correctness`, `grounded_recommendations`). Then re-run ASSERT on the same suite to show the optimized prompt's scenario-grounded gains.

> "DSPy is no longer optimizing a toy proxy — it's optimizing against the same scenario-grounded evaluator we trust for the model-swap decision."

(GEPA can be slow — precomputing the optimized run for the talk is fine; the point is the *signal*, not the live wall-clock.)

## Notes

- The tools use synthetic data — keep it that way for the workshop (no real bookings).
- Use placeholder env-var names in all materials; never commit real credentials.
- Trace capture is the recommended path (the judge can cite tool calls and routing). The wrapper degrades to a plain callable if Phoenix isn't installed — still scenario-grounded, just less trace evidence.

## Validation run (what this actually produced)

A live run on a shared, fixed 5-case suite — only the **target** model swapped (pipeline + judge held at `azure_ai/gpt-5.5`) — gave a genuinely *discriminating* per-dimension comparison:

| Dimension | gpt-5.5 | Claude-opus-4-5 | Mistral-Large-3 |
|---|---|---|---|
| **budget_adherence** | **0/5 fail (best)** | 1/5 fail | **3/5 fail (worst)** |
| **constraint_satisfaction** | 3/5 fail | **1/5 fail (best)** | 3/5 fail |
| tool_routing_correctness¹ | 5/5 | 5/5 | 5/5 |
| grounded_recommendations¹ | 5/5 | 5/5 | 5/5 |

This is the thesis in one table: on *this* scenario, **gpt-5.5 is strongest on budget math, Mistral is weakest, and Claude best respects constraints** — divergence a generic benchmark would never show.

> **¹ Run with trace capture for a complete picture.** Without traces the judge can't see tool calls, so `tool_routing_correctness` and `grounded_recommendations` flag uniformly (its own justification: *"no tool calls appear in the transcript"*). They're degraded *equally* across models, so they don't bias the budget/constraint comparison — but enable `WORKSHOP_TRACE=1` with a working Phoenix collector (`uv add arize-phoenix` in a clean env, then `phoenix serve`) to make all five dimensions valid.
