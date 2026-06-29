# ASSERT sample results: travel planner model swap (traced, n=100)

Committed outputs from a **trace-captured** ASSERT run across three comparable agentic models
(**gpt-5.5**, **Kimi-K2.6**, **DeepSeek-V4-Flash**). With trace capture on, ASSERT's judge sees the
agent's actual tool calls and routing, so the agentic dimensions (tool routing, grounding) are
real signal — not "no tool calls visible."

## Comparison (lower fail % = better)

The three runs are compared on the **55 test cases common to all three** (identical, traced cases —
see the methodology note below):

| Dimension | gpt-5.5 | Kimi-K2.6 | DeepSeek-V4-Flash |
|---|---:|---:|---:|
| budget_adherence | **2%** | 13% | 13% |
| constraint_satisfaction | **5%** | 13% | 27% |
| tool_routing_correctness | **7%** | 35% | 33% |
| grounded_recommendations | **35%** | 62% | 64% |
| overrefusal | **7%** | 15% | 18% |

**Interpretation:** on *this* travel-planner workflow, **gpt-5.5 is the most reliable across every
dimension** — it stays on budget, respects constraints, sequences its tools correctly, and grounds
its recommendations in tool outputs far more often than Kimi-K2.6 or DeepSeek-V4-Flash, which are
roughly comparable to each other (DeepSeek weaker on constraint satisfaction). This is the
"which model should I ship for this workflow?" answer a generic leaderboard can't give you.

The agentic dimensions are the payoff of trace capture: `tool_routing_correctness` (gpt-5.5 7% vs
~34% for the others) and `grounded_recommendations` are only meaningful because the judge can cite
the captured tool calls. `grounded_recommendations` is high for all three — even gpt-5.5 asserts
prices/options that aren't fully grounded in tool results ~35% of the time — a genuine, scenario-specific
finding worth a drill-down in the viewer.

> **Still directional, not a definitive ranking.** Single-pass judging by `gpt-5.5` (a self-grading
> confound worth noting — gpt-5.5 also judges itself), one run per model. For a hardened result, add
> a non-GPT cross-judge and/or judge repeats.

## Methodology note (why n=55 common)

ASSERT generates the test set with the (fixed) `gpt-5.5` generator. The gpt-5.5 and Kimi runs each
produced the **identical** 75-case suite; the DeepSeek run hit transient "invalid test_set payload"
generator failures and produced 55 cases, a strict **subset** of the 75. To keep the comparison
apples-to-apples, the table above is computed over the **55 test cases all three models actually share**
(identical traced inputs). The per-model raw outputs (75 / 75 / 55 cases) are committed in full below.

## Committed artifacts (full run output)

```
pamela-travel-planner-model-swap-n100/
├── suite.json, systematization.json, stratification.json, taxonomy.json, test_set.jsonl   # suite-level (75-case canonical)
├── gpt-5-5/            { config.yaml, manifest.json, metrics.json, scores.jsonl, inference_set.jsonl, .viewer/ }
├── kimi-k2-6/          { ... }
└── deepseek-v4-flash/  { ... }
```

`scores.jsonl` = per-case judge verdicts + justifications; `inference_set.jsonl` = full traced
transcripts (tool calls captured); `metrics.json` = rollups.

## View it in the local viewer

The viewer ships with [ASSERT](https://github.com/responsibleai/ASSERT). Clone it, copy these saved
results into its results dir, and launch:

```bash
git clone https://github.com/responsibleai/ASSERT
cp -r assert_eval/sample_results/pamela-travel-planner-model-swap-n100 ASSERT/artifacts/results/
cd ASSERT/viewer && npm install && npm run dev      # open http://localhost:5174
```

PowerShell:

```powershell
git clone https://github.com/responsibleai/ASSERT
Copy-Item assert_eval\sample_results\pamela-travel-planner-model-swap-n100 ASSERT\artifacts\results\ -Recurse
cd ASSERT\viewer; npm install; npm run dev          # open http://localhost:5174
```

Open the `pamela-travel-planner-model-swap-n100` suite, **compare `gpt-5-5` vs `kimi-k2-6` vs
`deepseek-v4-flash` by dimension**, and drill into a flagged row to read the judge's verdict cited
against the captured tool calls.

Regenerate from scratch with `WORKSHOP_TARGET_MODEL=<model> WORKSHOP_TRACE=1 uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=<run-name>`
(see `assert_eval/README.md` for the trace-capture setup).
