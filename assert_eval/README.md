# ASSERT guide

This folder adds an ASSERT eval for the travel-planner scenario. It keeps the travel tools and system prompt fixed, swaps only `WORKSHOP_TARGET_MODEL`, and scores the same generated cases across prompt-model variants. The entree question: **which model should you trust for this travel-planner workflow?**

## Files

| File | Role |
|---|---|
| `travel_planner_eval.yaml` | Scenario spec, generated test cases, and judge dimensions. |
| `travel_planner_target.py` | pydantic-ai wrapper around Pamela's travel tools and system prompt. |
| `sample_results/` | Committed traced n=100 ASSERT outputs (3 models). |

## Setup

```bash
uv pip install "git+https://github.com/responsibleai/ASSERT.git@main"
uv add arize-phoenix-otel openinference-instrumentation-langchain
```

> Trace-capture note: use `WORKSHOP_TRACE=1` to make tool routing and grounding dimensions valid. ASSERT's in-process tracer captures spans; no Phoenix server is required. Keep `openinference-instrumentation-langchain` installed, but remove `openinference-instrumentation-openai` if present because its pydantic incompatibility can corrupt pipeline calls.

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
WORKSHOP_TARGET_MODEL="gpt-5.5" WORKSHOP_TRACE=1 uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=gpt-5-5
WORKSHOP_TARGET_MODEL="Kimi-K2.6" WORKSHOP_TRACE=1 uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=kimi-k2-6
WORKSHOP_TARGET_MODEL="DeepSeek-V4-Flash" WORKSHOP_TRACE=1 uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=deepseek-v4-flash
```

PowerShell:

```powershell
$env:WORKSHOP_TARGET_MODEL = "gpt-5.5"
$env:WORKSHOP_TRACE = "1"
uv run assert-ai run --config assert_eval\travel_planner_eval.yaml --override run=gpt-5-5
```

Run from the repo root so `assert_eval.travel_planner_target:chat_sync` resolves.

## Static results for the DSPy finale

ASSERT saves every run to `artifacts/results/<suite>/<run>/`, including `scores.jsonl` and `metrics.json`. That means the eval scores persist and can be shown without re-running expensive DSPy loops.

For the finale, show both saved artifacts statically:

1. ASSERT eval scores per prompt-model variant.
2. DSPy's optimized prompt.

See [`sample_results/RESULTS.md`](sample_results/RESULTS.md) for the committed traced n=100 comparison and **full run artifacts** (`scores.jsonl`, `inference_set.jsonl`, `metrics.json`, plus the viewer cache) — with a one-line **copy-to-local-viewer** command so you can browse the runs side-by-side without re-running anything.

## Validation run: n=100, trace-captured

ASSERT's `gpt-5.5` generator produced identical 75-case suites for `gpt-5.5` and `Kimi-K2.6`; `DeepSeek-V4-Flash` hit transient generator failures and completed 55 cases. The table compares the 55 traced cases common to all three models; full raw outputs (75/75/55) are committed.

| Dimension | gpt-5.5 | Kimi-K2.6 | DeepSeek-V4-Flash |
|---|---:|---:|---:|
| **budget_adherence** (fail %, lower=better) | 2% | 13% | 13% |
| **constraint_satisfaction** (fail %, lower=better) | 5% | 13% | 27% |
| **tool_routing_correctness** (fail %, lower=better) | 7% | 35% | 33% |
| **grounded_recommendations** (fail %, lower=better) | 35% | 62% | 64% |
| **overrefusal** (fail %, lower=better) | 7% | 15% | 18% |

**Readout:** `gpt-5.5` is best across every dimension. `WORKSHOP_TRACE=1` makes tool routing and grounded recommendations valid signals because the judge can inspect the captured agent spans. `Kimi-K2.6` and `DeepSeek-V4-Flash` are roughly comparable, with DeepSeek weakest on constraint satisfaction.

Known caveats:

- Directional, not definitive: one run per model and no variance estimate.
- The judge is `gpt-5.5`, so self-grading bias is possible.
- Comparable percentages use the 55 common traced cases, even though the full per-model raw outputs are committed.
