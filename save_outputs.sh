#!/usr/bin/env bash

set -uo pipefail

cd "$(dirname "$0")"

export DEFER_PYDANTIC_BUILD=0

MODELS=(
    "DeepSeek-V4-Flash"
    "Kimi-K2.6"
    "Mistral-Large-3"
    "gpt-5.5"
)

PER_MODEL_EXAMPLES=(
    "single_llm_letter_counting"
    "single_llm_spatial_reasoning"
    "single_llm_self_calibration"
    "single_llm_multi_constraint"
    "rag_responses"
    "function_calling"
    "tool_loop_calculator"
    "tool_loop_code"
    "agent_trip_planner_pydanticai"
    "agent_trip_planner_langchain"
    "agent_trip_planner_maf"
)

mkdir -p outputs

for example in "${PER_MODEL_EXAMPLES[@]}"; do
    mkdir -p "outputs/$example"
    for model_name in "${MODELS[@]}"; do
        outfile="outputs/$example/$model_name.txt"
        echo "==> Running $example with $model_name ..."
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
            uv run "examples/$example.py" > "$outfile" 2>&1
        echo "    Saved to $outfile (exit code: $?)"
    done
done

# Anthropic examples (run once with default model)
ANTHROPIC_EXAMPLES=(
    "rag_messages"
    "anthropic_messages"
)

for example in "${ANTHROPIC_EXAMPLES[@]}"; do
    mkdir -p "outputs/$example"
    outfile="outputs/$example/claude-sonnet-4-5.txt"
    echo "==> Running $example (Anthropic) ..."
    uv run "examples/$example.py" > "$outfile" 2>&1
    echo "    Saved to $outfile (exit code: $?)"
done

# image_input (run once with default model)
mkdir -p "outputs/image_input"
echo "==> Running image_input ..."
uv run examples/image_input.py > "outputs/image_input/gpt-5.5.txt" 2>&1
echo "    Saved to outputs/image_input/gpt-5.5.txt (exit code: $?)"

# dspy_optimize (run once — takes ~6 minutes)
mkdir -p "outputs/dspy_optimize"
echo "==> Running dspy_optimize (this takes several minutes) ..."
uv run examples/dspy_optimize.py > "outputs/dspy_optimize/Mistral-Large-3.txt" 2>&1
echo "    Saved to outputs/dspy_optimize/Mistral-Large-3.txt (exit code: $?)"

echo
echo "Done! All outputs saved to outputs/"
