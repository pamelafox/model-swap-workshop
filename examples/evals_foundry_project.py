"""
Eval using openai.evals.create: Run evaluations via Foundry's hosted eval service.

This uses the OpenAI Evals API through a Foundry project to run built-in
evaluators (groundedness, tool call accuracy) against model outputs.
Results are viewable in the Foundry portal.

Unlike evals_llm_judge.py (which runs locally), this version uploads test data
to Foundry and runs evaluation server-side with full observability.

Requirements:
    - A Foundry project (FOUNDRY_PROJECT_ENDPOINT env var)
    - azure-ai-projects package

Usage:
    uv run examples/evals_openai.py
"""

import json
import os
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
model_deployment = os.environ.get("FOUNDRY_OPENAI_DEPLOYMENT", "gpt-5.5")

OUTPUT_DIR = Path(__file__).parent / "eval_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Authenticate — try DefaultAzureCredential first, fall back to azd credential
try:
    credential = DefaultAzureCredential()
    # Force a token fetch to verify
    credential.get_token("https://management.azure.com/.default")
except Exception:
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if tenant_id:
        credential = AzureDeveloperCliCredential(tenant_id=tenant_id)
    else:
        credential = AzureDeveloperCliCredential()

project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)

# ---------------------------------------------------------------------------
# Test data: RAG groundedness scenario
# Each row has a query, context (sources), and a pre-baked model response
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "search_knowledge_base",
        "type": "function",
        "description": "Search the insect knowledge base for relevant information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant documents.",
                }
            },
            "required": ["query"],
        },
    },
]

# Load our existing groundedness test data
data_path = Path(__file__).parent / "evals_groundedness_data.jsonl"
dataset_path = OUTPUT_DIR / "evals_openai_dataset.jsonl"

# Augment with tool_definitions and ground_truth for the eval API
with open(data_path) as infile, open(dataset_path, "w") as outfile:
    for line in infile:
        item = json.loads(line)
        augmented = {
            "query": item["query"],
            "context": item["context"],
            "response": item["response"],
            "model": item["model"],
            "ground_truth": (
                "Carpenter bees bore into wood to create nests. "
                "The sources do not contain information about honey bee nest construction."
            ),
            "tool_definitions": TOOL_DEFINITIONS,
        }
        outfile.write(json.dumps(augmented) + "\n")

print(f"Prepared dataset: {dataset_path}")

# ---------------------------------------------------------------------------
# 1. Upload the test dataset
# ---------------------------------------------------------------------------
dataset = project_client.datasets.upload_file(
    name="model-swap-workshop-eval-data",
    version=str(int(time.time())),
    file_path=str(dataset_path),
)
print(f"Uploaded dataset: {dataset.id}")

# ---------------------------------------------------------------------------
# 2. Define evaluators (testing criteria)
# ---------------------------------------------------------------------------
testing_criteria = [
    {
        "type": "azure_ai_evaluator",
        "name": "Groundedness",
        "evaluator_name": "builtin.groundedness",
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{item.response}}",
            "context": "{{item.context}}",
        },
        "initialization_parameters": {"deployment_name": model_deployment},
    },
    {
        "type": "azure_ai_evaluator",
        "name": "Relevance",
        "evaluator_name": "builtin.relevance",
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{item.response}}",
        },
        "initialization_parameters": {"deployment_name": model_deployment},
    },
    {
        "type": "azure_ai_evaluator",
        "name": "Response Completeness",
        "evaluator_name": "builtin.response_completeness",
        "data_mapping": {
            "ground_truth": "{{item.ground_truth}}",
            "response": "{{item.response}}",
        },
        "initialization_parameters": {"deployment_name": model_deployment},
    },
]

# ---------------------------------------------------------------------------
# 3. Create the evaluation
# ---------------------------------------------------------------------------
openai_client = project_client.get_openai_client()

data_source_config = {
    "type": "custom",
    "item_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "context": {"type": "string"},
            "response": {"type": "string"},
            "model": {"type": "string"},
            "ground_truth": {"type": "string"},
            "tool_definitions": {"type": "array"},
        },
        "required": ["query", "response"],
    },
    "include_sample_schema": False,
}

evaluation = openai_client.evals.create(
    name="Model Swap Workshop - Groundedness Eval",
    data_source_config=data_source_config,
    testing_criteria=testing_criteria,
)
print(f"Created evaluation: {evaluation.id}")

# ---------------------------------------------------------------------------
# 4. Create a run with our pre-computed responses (no model invocation needed)
# ---------------------------------------------------------------------------
eval_run = openai_client.evals.runs.create(
    eval_id=evaluation.id,
    name="Groundedness across models",
    data_source={
        "type": "jsonl",
        "source": {
            "type": "file_id",
            "id": dataset.id,
        },
    },
)
print(f"Evaluation run started: {eval_run.id}  status: {eval_run.status}")

# ---------------------------------------------------------------------------
# 5. Poll until the run completes
# ---------------------------------------------------------------------------
print("Polling for completion", end="", flush=True)
while True:
    run = openai_client.evals.runs.retrieve(run_id=eval_run.id, eval_id=evaluation.id)
    if run.status in ("completed", "failed", "canceled"):
        break
    print(".", end="", flush=True)
    time.sleep(5)

print(f"\nRun finished — status: {run.status}")
if hasattr(run, "report_url") and run.report_url:
    print(f"Report URL: {run.report_url}")

# ---------------------------------------------------------------------------
# 6. Retrieve and display results
# ---------------------------------------------------------------------------
items = list(openai_client.evals.runs.output_items.list(run_id=run.id, eval_id=evaluation.id))

output_path = OUTPUT_DIR / "evals_openai_results.json"
with open(output_path, "w") as f:
    json.dump(
        [item.to_dict() if hasattr(item, "to_dict") else str(item) for item in items],
        f,
        indent=2,
    )

print(f"\nOutput items ({len(items)}) saved to {output_path}")

# Print summary
print("\n" + "=" * 60)
print("  EVALUATION RESULTS")
print("=" * 60)
for item in items:
    item_dict = item.to_dict() if hasattr(item, "to_dict") else {}
    results = item_dict.get("results", [])
    sample = item_dict.get("sample", {})
    # Try to get the model name from the dataset item
    dataset_item = item_dict.get("dataset_item", {})
    model_name = dataset_item.get("model", "unknown")
    print(f"\n  Model: {model_name}")
    for r in results:
        name = r.get("name", "unknown")
        score = r.get("score")
        passed = r.get("passed")
        status = "✅" if passed else "❌"
        print(f"    {status} {name}: {score}")
