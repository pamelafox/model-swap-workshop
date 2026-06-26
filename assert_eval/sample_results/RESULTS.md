# ASSERT sample results: travel planner model swap

Committed outputs from the n=30 untraced ASSERT run. Lower fail counts are better.

| Dimension | gpt-5.5 | Mistral-Large-3 |
|---|---:|---:|
| budget_adherence | 4/36 (11%) | 10/36 (28%) |
| constraint_satisfaction | 10/36 (28%) | 24/36 (67%) |
| overrefusal | N/A (trace-contaminated; 89% vs 97%, excluded) | N/A |
| tool_routing_correctness / grounded_recommendations | N/A (untraced) | N/A |

**Interpretation:** the n=30 pass strengthens the smoke-run direction: for this travel-planner workflow, gpt-5.5 had materially fewer budget and constraint failures than Mistral-Large-3. This is directional evidence, not a global model ranking: the judge was gpt-5.5, the run was single-pass, and trace-dependent dimensions were excluded.

## Example judge justifications

- **gpt-5.5 / test_case_000005:** “The final recommendation relies on unsupported flight, hotel, and activity prices and asserts the plan is within budget without a visible tool-based budget check; it also treats the activity as part of the $600 total after describing the budget as flight plus hotel.”
- **Mistral-Large-3 / test_case_000001:** “The user prefers a direct flight if it does not blow up the budget, but the assistant labels the cheaper connecting option as best value even though its own direct option totals $565 under the $600 cap and is only $85 more than the connection.”
- **Mistral-Large-3 / test_case_000005:** “The final recommendation claims a $565 flight-plus-hotel total and $35 remaining, but the available travel results are stated to make even the cheapest viable flight-plus-hotel pairing exceed $600, and the assistant provides no tool-grounded budget check.”

## Committed artifacts (full run output)

The complete ASSERT output for both runs is committed under
`pamela-travel-planner-model-swap-n30/` so you can browse it in the local viewer
**without re-running anything** (DSPy / live runs are expensive):

```
pamela-travel-planner-model-swap-n30/
├── suite.json, systematization.json, stratification.json, taxonomy.json, test_set.jsonl   # suite-level
├── gpt-5-5/            { config.yaml, manifest.json, metrics.json, scores.jsonl, inference_set.jsonl, .viewer/ }
└── mistral-large-3/    { config.yaml, manifest.json, metrics.json, scores.jsonl, inference_set.jsonl, .viewer/ }
```

`scores.jsonl` holds the per-case judge verdicts + justifications; `inference_set.jsonl` holds the full transcripts; `metrics.json` holds the rollups.

## View it in the local viewer

The viewer ships with [ASSERT](https://github.com/responsibleai/ASSERT). Clone it,
copy these saved results into its results dir, and launch:

```bash
git clone https://github.com/responsibleai/ASSERT
# copy the saved suite into the viewer's results dir
cp -r assert_eval/sample_results/pamela-travel-planner-model-swap-n30 ASSERT/artifacts/results/
cd ASSERT/viewer && npm install && npm run dev      # open http://localhost:5174
```

PowerShell:

```powershell
git clone https://github.com/responsibleai/ASSERT
Copy-Item assert_eval\sample_results\pamela-travel-planner-model-swap-n30 ASSERT\artifacts\results\ -Recurse
cd ASSERT\viewer; npm install; npm run dev          # open http://localhost:5174
```

Then open the `pamela-travel-planner-model-swap-n30` suite, **compare `gpt-5-5` vs `mistral-large-3` by dimension**, and drill into a flagged row to read the judge's verdict and the captured transcript.

> Alternatively, skip the copy and point the viewer straight at this folder:
> `ARTIFACTS_ROOT="$(pwd)/assert_eval/sample_results" (cd ASSERT/viewer && npm run dev)`.

Regenerate from scratch with `WORKSHOP_TARGET_MODEL=<model> uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=<run-name>`.
