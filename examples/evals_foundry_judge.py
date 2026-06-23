"""
LLM judge evaluation: Use azure-ai-evaluation to score RAG groundedness.

Runs the GroundednessEvaluator against pre-recorded RAG outputs from different
models. The test data contains responses to a question about bee nesting where
the sources only cover carpenter bees — models that hallucinate honey bee
facts should score low on groundedness.

Requirements:
    uv add azure-ai-evaluation

Usage:
    uv run examples/evals_llm_judge.py
"""

import os
from pathlib import Path

import rich
from azure.ai.evaluation import (
    AzureOpenAIModelConfiguration,
    GroundednessEvaluator,
    evaluate,
)
from dotenv import load_dotenv

load_dotenv()

# Use the same Foundry endpoint and deployment attendees already have configured
model_config: AzureOpenAIModelConfiguration = {
    "azure_endpoint": os.environ["FOUNDRY_MODELS_ENDPOINT"],
    "azure_deployment": os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", "gpt-5.5"),
    "api_key": os.environ["FOUNDRY_API_KEY"],
}

groundedness_eval = GroundednessEvaluator(model_config, is_reasoning_model=True)

# Run bulk evaluation over the test data
script_dir = Path(__file__).parent
data_path = script_dir / "evals_groundedness_data.jsonl"
output_path = script_dir / "evals_groundedness_results.jsonl"

print("Running groundedness evaluation across model outputs...")
print(f"Test data: {data_path}")
print(f"Judge model: {model_config['azure_deployment']}")
print()

result = evaluate(
    data=data_path,
    evaluators={"groundedness": groundedness_eval},
    evaluator_config={
        "default": {
            "query": "${data.query}",
            "response": "${data.response}",
            "context": "${data.context}",
        }
    },
    output_path=output_path,
)

# Print results
print("\n" + "=" * 60)
print("  GROUNDEDNESS RESULTS")
print("=" * 60)

# Overall metrics
metrics = result.get("metrics", {})
avg_score = metrics.get("groundedness.groundedness", "N/A")
pass_rate = metrics.get("groundedness.groundedness_passed", "N/A")
print(f"\n  Average groundedness score: {avg_score} / 5")
print(f"  Pass rate: {pass_rate}")

# Per-row results
rows = result.get("rows", [])
if rows:
    print(f"\n  {'Model':<20} {'Score':<8} {'Pass?':<7} {'Reasoning'}")
    print(f"  {'-'*20} {'-'*8} {'-'*7} {'-'*40}")
    for row in rows:
        model = row.get("inputs.model", "unknown")
        score = row.get("outputs.groundedness.groundedness", "?")
        passed = row.get("outputs.groundedness.groundedness_result", "?")
        reason = row.get("outputs.groundedness.groundedness_reason", "")
        # Truncate reason for display
        reason_short = reason[:55] + "..." if len(reason) > 55 else reason
        print(f"  {model:<20} {score:<8} {passed:<7} {reason_short}")

print(f"\n  Full results written to: {output_path}")
