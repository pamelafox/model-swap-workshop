# Scenario-grounded model-swap evals with ASSERT

> **Thesis for this segment:** *Evaluate your model upgrades in the context of **your** scenarios — not generic benchmarks.*

This folder adds an [ASSERT](https://github.com/responsibleai/ASSERT) evaluation for the travel-planner scenario. To compare models **across providers** (OpenAI-endpoint *and* Claude) on the *same* agent, the target wrapper rebuilds the planner on **pydantic-ai** — the framework Pamela already uses for her cross-provider examples — reusing her **exact tools and system prompt**. Only the model client changes between runs. It upgrades the workshop's generic judges (programmatic checks, RAG groundedness, single tool-call accuracy) into a **scenario-grounded judge** that scores the travel-planning behavior — budget, constraints, and (with trace capture) tool routing and grounding — against the same scenario as you swap models.

> **Fidelity note:** this is "same tools + same system prompt, provider-aware wrapper," **not** byte-identical to her LangChain agent. Claude additionally runs with extended thinking enabled (part of the target configuration). So differences reflect model + provider-client behavior on this scenario, which is what a real model-swap decision faces.

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
| **Target** (the agent under test) | the provider-aware pydantic-ai wrapper (your tools + system prompt) | `FOUNDRY_MODELS_ENDPOINT` + `FOUNDRY_API_KEY` (OpenAI models); `FOUNDRY_ANTHROPIC_MODELS_ENDPOINT` + `FOUNDRY_ANTHROPIC_API_KEY` (Claude). Pick the model with **`WORKSHOP_TARGET_MODEL`** |
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

Hold the eval spec fixed; change only the **target** model via **`WORKSHOP_TARGET_MODEL`** (names starting with `claude` route to the Foundry Anthropic endpoint; everything else to the OpenAI-compatible endpoint):

```bash
WORKSHOP_TARGET_MODEL="gpt-5.5"          assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=gpt-55
WORKSHOP_TARGET_MODEL="claude-opus-4-5"  assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=claude-opus-4-5
WORKSHOP_TARGET_MODEL="Mistral-Large-3"  assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=mistral-large-3
```

PowerShell:

```powershell
$env:WORKSHOP_TARGET_MODEL = "gpt-5.5"
assert-ai run --config assert_eval\travel_planner_eval.yaml --override run=gpt-55
```

Run `assert-ai run` from the repo root so the `assert_eval.travel_planner_target:chat_sync` callable resolves. The same fixed suite (taxonomy + test set) is generated once and reused across runs, so every model is judged on identical cases.

For the trace-dependent dimensions (tool routing, grounding), set `WORKSHOP_TARGET_MODEL=... WORKSHOP_TRACE=1` with a working Phoenix collector running (`uv add arize-phoenix` in a clean env, then `phoenix serve`).

## See it in the viewer (the payoff moment)

```bash
git clone https://github.com/responsibleai/ASSERT
cd ASSERT/viewer && npm install && npm run dev   # http://localhost:5174
```

Point the viewer at the run's `artifacts/results/` (`ARTIFACTS_ROOT`), open the `pamela-travel-planner-model-swap` suite, and **compare runs by dimension**. For the drilldown, pick a case where the **final answer reads plausibly but the scenario rubric catches a real failure** — e.g. a confident itinerary that *skipped `check_budget`*, suggested an activity *before* computing the remaining budget, or violated the direct-flight-under-$100 rule. That's the point a skeptic can't get from eyeballing the output. (Tool-cited drilldowns require a **traced** run — see below.)

## Talk beats (drop-in to your existing arc)

| Your beat | ASSERT moment | Why it lands |
|---|---|---|
| Opening premise | "Today the eval stays fixed while the model changes." Show the config as the scenario contract. | Moves from "watch it break" to "measure what broke." |
| Parts 1–5 | Keep as-is — label them capability probes, not app evals. | Sets up the generic-vs-scenario contrast. |
| Part 6 travel agent | Run the planner normally, then run `assert-ai run` against it. | Converts "watch behavior" into "measure behavior." |
| Part 7 evals | Replace/augment the generic judge with the ASSERT travel-planner eval. | The evaluator is derived from *your* scenario spec. |
| **Viewer compare** | `gpt-5.5` vs `Claude`/`Mistral` per dimension; open one drilldown. | **The main proof of the thesis.** Use a **traced, precomputed** run as the live artifact so the tool-routing/grounding dimensions are valid and the judge can cite tool calls. |
| Part 8 DSPy | Use ASSERT scores as the optimization signal; re-run ASSERT after GEPA. | Closes the loop: measure → optimize → re-measure. |
| Recap | "Hold the scenario fixed, swap the model, compare scenario failures, optimize what matters." | Clean takeaway. |

### Lines to say

> "We're not asking whether Kimi beats Mistral on a generic benchmark. We're asking: when *this* travel planner has to stay under budget, prefer direct flights, validate tool results, and suggest an activity with the remaining budget — which model regresses *our* scenario?"

> **The punchline:** a "better" model can still regress on budget validation or tool dependency order — and ASSERT makes that visible, per dimension, on your scenario.

## DSPy finale, closed-loop

Keep your GEPA finale, but swap the objective: instead of the toy `constraint_metric`, optimize against ASSERT's per-dimension scores (e.g. `budget_adherence`, `constraint_satisfaction`). Then re-run ASSERT to show the optimized prompt's scenario-grounded gains.

> "DSPy is no longer optimizing a toy proxy — it's optimizing against a scenario-grounded evaluator built from the spec."

> **Avoid the reward-hacking trap.** Optimizing a prompt against a judge and then scoring it with the *same judge on the same cases* overfits to the judge, not to travel-planning quality. Make the finale honest:
> - **Split scenarios** — optimize on an ASSERT-generated *training* suite, then report on a **held-out** ASSERT suite the optimizer never saw.
> - **Cross-check** the held-out run with a **second judge** (or human spot-checks) so gains aren't just judge self-satisfaction.
> - Present this as a **closed-loop optimization candidate**, not proof of general improvement.

(GEPA can be slow — precomputing the optimized run for the talk is fine; the point is the *signal*, not the live wall-clock.)

## Notes

- The tools use synthetic data — keep it that way for the workshop (no real bookings).
- Use placeholder env-var names in all materials; never commit real credentials.
- Trace capture is the recommended path (the judge can cite tool calls and routing). The wrapper degrades to a plain callable if Phoenix isn't installed — still scenario-grounded, just less trace evidence.

## Validation run (what this actually produced)

This was validated with a **smoke run** — a shared, fixed 5-case suite, only the **target** model swapped (pipeline + judge held at `azure_ai/gpt-5.5`), a **single judge pass**, and **no trace capture**. Read it as **directional**, not a definitive model ranking. Of the five judge dimensions, only the two text-judgeable ones are interpretable in an untraced run:

| Dimension | gpt-5.5 | Claude-opus-4-5 | Mistral-Large-3 |
|---|---|---|---|
| **budget_adherence** (fail count, lower=better) | 0/5 | 1/5 | 3/5 |
| **constraint_satisfaction** (fail count, lower=better) | 3/5 | 1/5 | 3/5 |
| tool_routing_correctness | N/A¹ | N/A¹ | N/A¹ |
| grounded_recommendations | N/A¹ | N/A¹ | N/A¹ |
| overrefusal | N/A² | N/A² | N/A² |

**What it shows:** even at n=5, ASSERT surfaced **candidate scenario regressions worth investigating** — Mistral missed budget math in 3 of 5 cases where gpt-5.5 missed none, and Claude had the fewest constraint misses. That's a *pointer*, not a verdict: a generic benchmark wouldn't tell you whether **this** travel-planner workflow regressed, but n=5 + one judge pass can't rank models conclusively. A larger **n=30 scenario** run is included to firm this up.

> **¹ Trace unavailable — not a model failure.** Run untraced, the judge can't see tool calls (its own words: *"no tool calls appear in the transcript"*), so these dimensions are measurement-invalid and excluded from comparison, not scored as failures. Enable `WORKSHOP_TRACE=1` with a Phoenix collector to make them valid.
>
> **² Likely trace-contaminated too.** The untraced `overrefusal` verdicts keyed off the same "no tool-grounded help visible" signal, so they're excluded here pending a traced re-run and a rationale audit.
>
> **Known confounds to state out loud:** (a) the judge is `gpt-5.5`, the same family as one target — a possible self-preference bias; mitigate with a non-GPT cross-judge or judge repeats. (b) single judge pass = no variance estimate. (c) n=5 is a smoke sample. Treat all numbers as gpt-5.5-judged, single-pass, directional until the n=30 (and ideally cross-judged) results land.
