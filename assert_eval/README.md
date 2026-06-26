# ASSERT speaker note: scenario evals for model swaps

**Thesis:** evaluate model upgrades against *your* workflow, not generic benchmarks.

This folder adds an ASSERT eval for the travel-planner scenario. It keeps the travel tools and system prompt fixed, swaps only `WORKSHOP_TARGET_MODEL`, and scores the same generated cases across prompt-model variants. The entree question: **which model should you trust for this travel-planner workflow?**

Claude is on a personal account and out of scope for this lab; the same pydantic-ai target pattern extends to it if you have access.

## Files

| File | Role |
|---|---|
| `travel_planner_eval.yaml` | Scenario spec, generated test cases, and judge dimensions. |
| `travel_planner_target.py` | pydantic-ai wrapper around Pamela's travel tools and system prompt. |
| `sample_results/` | Committed n=30 ASSERT outputs for the talk. |

## Setup

```bash
uv add assert-ai arize-phoenix-otel openinference-instrumentation-langchain
```

ASSERT uses two model paths:

| Path | Used by | Env vars |
|---|---|---|
| **Target** | agent under test via Foundry OpenAI-compatible endpoint | `FOUNDRY_MODELS_ENDPOINT`, `FOUNDRY_API_KEY`, optional `WORKSHOP_TARGET_MODEL` |
| **Pipeline** | ASSERT generation + judge in `travel_planner_eval.yaml` | `AZURE_API_BASE`, `AZURE_AI_API_KEY`, `AZURE_API_KEY` |

Use placeholders only; never commit keys.

```bash
export AZURE_API_BASE="$FOUNDRY_MODELS_ENDPOINT"
export AZURE_AI_API_KEY="$FOUNDRY_API_KEY"
export AZURE_API_KEY="$FOUNDRY_API_KEY"
```

The pipeline model stays fixed at `azure_ai/gpt-5.5` while you swap the target. `temperature` is omitted because the gpt-5 family only accepts the provider default.

## Run the model-swap loop

```bash
WORKSHOP_TARGET_MODEL="gpt-5.5"         uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=gpt-5-5
WORKSHOP_TARGET_MODEL="Mistral-Large-3" uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=mistral-large-3
```

PowerShell:

```powershell
$env:WORKSHOP_TARGET_MODEL = "gpt-5.5"
uv run assert-ai run --config assert_eval\travel_planner_eval.yaml --override run=gpt-5-5
```

Run from the repo root so `assert_eval.travel_planner_target:chat_sync` resolves. For trace-dependent dimensions, set `WORKSHOP_TRACE=1` and run a Phoenix collector; otherwise routing/grounding are measurement-invalid, not model failures.

## Static results for the DSPy finale

ASSERT saves every run to `artifacts/results/<suite>/<run>/`, including `scores.jsonl` and `metrics.json`. That means the eval scores persist and can be shown without re-running expensive DSPy loops.

For the finale, show both saved artifacts statically:

1. ASSERT eval scores per prompt-model variant.
2. DSPy's optimized prompt.

See `sample_results/RESULTS.md` for the committed n=30 comparison and raw outputs.

## Talk beats

| Beat | What to show | Why it lands |
|---|---|---|
| Premise | “Hold the scenario fixed while the model changes.” | Moves from vibes to measured regressions. |
| Travel agent | Run the planner normally, then run ASSERT against it. | Converts behavior into scenario scores. |
| **Viewer compare** | `gpt-5.5` vs `Mistral-Large-3` by dimension. | Answers “which model for this workflow?” |
| DSPy | Use ASSERT scores as the optimization signal, then re-run ASSERT. | Closes measure → optimize → re-measure. |

Line to say:

> “We’re not asking whether one model wins a benchmark. We’re asking: when this travel planner must stay under budget, prefer direct flights, and suggest an activity from remaining budget, which model regresses our scenario?”

## Validation run: n=30, untraced

Shared fixed n=30 suite; target swapped; pipeline + judge held at `azure_ai/gpt-5.5`; single judge pass; no trace capture. Read as directional, not a definitive ranking.

| Dimension | gpt-5.5 | Mistral-Large-3 |
|---|---:|---:|
| **budget_adherence** (fail count, lower=better) | 4/36 (11%) | 10/36 (28%) |
| **constraint_satisfaction** (fail count, lower=better) | 10/36 (28%) | 24/36 (67%) |
| overrefusal | N/A (trace-contaminated; 89% vs 97%, excluded) | N/A |
| tool_routing_correctness / grounded_recommendations | N/A (untraced) | N/A |

**Readout:** the smoke-run direction holds and strengthens. On this travel scenario, `gpt-5.5` has materially fewer budget and constraint failures than `Mistral-Large-3`. Still: one `gpt-5.5` judge, one pass, untraced evidence. Treat it as directional evidence for **which model to trust for this workflow**, not a global ranking.

Known caveats:

- The judge is `gpt-5.5`, so self-grading bias is possible.
- Single judge pass means no variance estimate.
- Untraced runs cannot validly score tool routing or grounding, and overrefusal looked trace-contaminated.
