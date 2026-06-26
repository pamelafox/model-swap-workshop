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

## Raw outputs

- `gpt-5.5/scores.jsonl`
- `gpt-5.5/metrics.json`
- `mistral-large-3/scores.jsonl`
- `mistral-large-3/metrics.json`

Regenerate with `WORKSHOP_TARGET_MODEL=<model> uv run assert-ai run --config assert_eval/travel_planner_eval.yaml --override run=<run-name>`.
