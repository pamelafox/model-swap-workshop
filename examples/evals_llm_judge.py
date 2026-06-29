"""
LLM judge evaluation: Score RAG groundedness with a direct LLM call.

Instead of using an eval SDK, this makes a straight call to an LLM with a
groundedness prompt (inspired by azure-ai-evaluation's GroundednessEvaluator)
but simplified to a binary pass/fail verdict.

Runs against the same pre-recorded RAG outputs from different models.
The test data contains responses to a question about bee nesting where the
sources only cover carpenter bees — models that hallucinate honey bee facts
should fail on groundedness.

Usage:
    uv run examples/evals_llm_judge.py
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

JUDGE_MODEL = "gpt-5.5"

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"]
api_key = os.environ["FOUNDRY_API_KEY"]

client = OpenAI(base_url=endpoint, api_key=api_key)

GROUNDEDNESS_SYSTEM_PROMPT = """\
You are an expert evaluator assessing whether a RESPONSE is grounded in the provided CONTEXT.

**Groundedness** means the response only contains claims that are supported by the context. \
A grounded response does not introduce facts, details, or assertions beyond what the context provides.

Your task: determine whether the RESPONSE passes or fails groundedness.

Rules:
- PASS: Every factual claim in the response is supported by the context, OR the response \
explicitly states that the information is not available in the context.
- FAIL: The response contains ANY factual claim not supported by the context, even if that \
claim is generally true. Using outside knowledge counts as a failure.

Respond with a JSON object containing exactly these fields:
- "verdict": "pass" or "fail"
- "reason": A brief explanation (1-2 sentences) of why the response passed or failed.
"""

GROUNDEDNESS_USER_TEMPLATE = """\
CONTEXT:
{context}

QUERY:
{query}

RESPONSE:
{response}

Evaluate the groundedness of the RESPONSE given the CONTEXT. \
Remember: any claim not directly supported by the context is a failure, \
even if generally true."""


def judge_groundedness(query: str, context: str, response: str) -> dict:
    """Call the judge model to evaluate groundedness. Returns {"verdict": ..., "reason": ...}."""
    user_message = GROUNDEDNESS_USER_TEMPLATE.format(
        context=context, query=query, response=response
    )
    result = client.responses.create(
        model=JUDGE_MODEL,
        input=[
            {"role": "system", "content": GROUNDEDNESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        text={"format": {"type": "json_object"}},
        store=False,
    )
    # Extract text from response
    text = ""
    for item in result.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text = content.text
                    break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "error", "reason": f"Could not parse judge output: {text[:100]}"}


def main():
    # Load test data
    data_path = os.path.join(os.path.dirname(__file__), "evals_groundedness_data.jsonl")
    with open(data_path) as f:
        test_cases = [json.loads(line) for line in f if line.strip()]

    print("Running groundedness evaluation with LLM judge")
    print(f"Judge model: {JUDGE_MODEL}")
    print(f"Test cases: {len(test_cases)}")
    print()

    results = []
    for case in test_cases:
        model = case.get("model", "unknown")
        judgment = judge_groundedness(
            query=case["query"],
            context=case["context"],
            response=case["response"],
        )
        verdict = judgment.get("verdict", "error")
        reason = judgment.get("reason", "")
        results.append({"model": model, "verdict": verdict, "reason": reason})

        icon = "✅" if verdict == "pass" else "❌" if verdict == "fail" else "⚠️"
        print(f"  {icon} {model:<20} {verdict:<6} {reason}")

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    models = sorted(set(r["model"] for r in results))
    print(f"  {'Model':<20} {'Passed':<8} {'Failed':<8} {'Score'}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8}")
    for model in models:
        model_results = [r for r in results if r["model"] == model]
        passed = sum(1 for r in model_results if r["verdict"] == "pass")
        failed = sum(1 for r in model_results if r["verdict"] == "fail")
        total = len(model_results)
        print(f"  {model:<20} {passed:<8} {failed:<8} {passed}/{total}")


if __name__ == "__main__":
    main()
