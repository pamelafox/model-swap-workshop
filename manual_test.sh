#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

# Workaround for openai-python#1306 / pydantic#7713:
# responses.parse() calls model_dump() on SDK objects built with model_construct(),
# which hits a MockValSer crash when pydantic defers model builds (the default).
export DEFER_PYDANTIC_BUILD=0

MODELS=(
    "DeepSeek-V4-Flash"
    "DeepSeek-V4-Pro"
    "Kimi-K2.6"
    "Mistral-Large-3"
    "gpt-5.5"
)

EXAMPLES=(
    "single_llm_letter_counting"
    "single_llm_spatial_reasoning"
    "single_llm_self_calibration"
    "single_llm_multi_constraint"
    "rag_responses"
    "rag_messages"
    "anthropic_messages"
    "image_input"
    "function_calling"
    "tool_loop_calculator"
    "tool_loop_code"
    "agent_trip_planner_pydanticai"
    "agent_trip_planner_langchain"
    "agent_trip_planner_maf"
    # Evals are excluded from manual testing due to expense (they make many LLM calls)
    # evals_basic, evals_foundry_judge, evals_agent, evals_foundry_project
    # dspy_optimize is excluded as it takes ~6 minutes to run
)

if [[ -n "${ONLY_MODEL:-}" ]]; then
    model_found=0
    for model_name in "${MODELS[@]}"; do
        if [[ "$model_name" == "$ONLY_MODEL" ]]; then
            model_found=1
            break
        fi
    done

    if [[ $model_found -eq 0 ]]; then
        echo "Unknown ONLY_MODEL: $ONLY_MODEL"
        echo "Available models: ${MODELS[*]}"
        exit 2
    fi

    MODELS=("$ONLY_MODEL")
fi

if [[ -n "${ONLY_EXAMPLE:-}" ]]; then
    example_found=0
    for example_name in "${EXAMPLES[@]}"; do
        if [[ "$example_name" == "$ONLY_EXAMPLE" ]]; then
            example_found=1
            break
        fi
    done

    if [[ $example_found -eq 0 ]]; then
        echo "Unknown ONLY_EXAMPLE: $ONLY_EXAMPLE"
        echo "Available examples: ${EXAMPLES[*]}"
        exit 2
    fi
fi

PASS_COUNT=0
FAIL_COUNT=0

run_case() {
    local label="$1"
    shift

    echo
    echo "==> $label"
    if "$@"; then
        echo "PASS: $label"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "FAIL: $label"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

should_run_example() {
    local example_name="$1"
    if [[ -z "${ONLY_EXAMPLE:-}" ]]; then
        return 0
    fi
    [[ "$example_name" == "$ONLY_EXAMPLE" ]]
}

run_example_case() {
    local example_name="$1"
    local label="$2"
    shift 2

    if should_run_example "$example_name"; then
        run_case "$label" "$@"
    fi
}

run_for_model() {
    local model_name="$1"

    echo
    echo "########################################"
    echo "Testing model: $model_name"
    echo "########################################"

    run_example_case "single_llm_letter_counting" "$model_name :: single_llm_letter_counting" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/single_llm_letter_counting.py

    run_example_case "single_llm_spatial_reasoning" "$model_name :: single_llm_spatial_reasoning" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/single_llm_spatial_reasoning.py

    run_example_case "single_llm_self_calibration" "$model_name :: single_llm_self_calibration" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/single_llm_self_calibration.py

    run_example_case "single_llm_multi_constraint" "$model_name :: single_llm_multi_constraint" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/single_llm_multi_constraint.py

    run_example_case "rag_responses" "$model_name :: rag_responses" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/rag_responses.py

    run_example_case "function_calling" "$model_name :: function_calling" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/function_calling.py

    run_example_case "tool_loop_calculator" "$model_name :: tool_loop_calculator" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/tool_loop_calculator.py

    run_example_case "tool_loop_code" "$model_name :: tool_loop_code" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/tool_loop_code.py

    run_example_case "agent_trip_planner_pydanticai" "$model_name :: agent_trip_planner_pydanticai" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agent_trip_planner_pydanticai.py

    run_example_case "agent_trip_planner_langchain" "$model_name :: agent_trip_planner_langchain" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agent_trip_planner_langchain.py

    run_example_case "agent_trip_planner_maf" "$model_name :: agent_trip_planner_maf" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agent_trip_planner_maf.py

}

for model_name in "${MODELS[@]}"; do
    run_for_model "$model_name"
done

# Anthropic/Claude examples — run once (not per OpenAI model)
run_example_case "rag_messages" "claude :: rag_messages" \
    uv run examples/rag_messages.py

run_example_case "anthropic_messages" "claude :: anthropic_messages" \
    uv run examples/anthropic_messages.py

# image_input doesn't support FOUNDRY_OPENAI_DEPLOYMENT override, run once
run_example_case "image_input" "default :: image_input" \
    uv run examples/image_input.py

echo
echo "========================================"
echo "Manual test summary"
echo "PASS: $PASS_COUNT"
echo "FAIL: $FAIL_COUNT"
echo "========================================"

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi