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
    "agentframework_agent"
    "langchain_agent"
    "pydanticai_agent"
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

    run_example_case "rag_messages" "$model_name :: rag_messages" \
        uv run examples/rag_messages.py

    run_example_case "anthropic_messages" "$model_name :: anthropic_messages" \
        env FOUNDRY_ANTHROPIC_DEPLOYMENT="$model_name" \
        uv run examples/anthropic_messages.py

    run_example_case "agentframework_agent" "$model_name :: agentframework_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_agent.py

    run_example_case "agentframework_agent" "$model_name :: agentframework_agent (claude)" \
        env FOUNDRY_ANTHROPIC_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_agent.py

    run_example_case "langchain_agent" "$model_name :: langchain_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/langchain_agent.py

    run_example_case "langchain_agent" "$model_name :: langchain_agent (claude)" \
        env FOUNDRY_ANTHROPIC_DEPLOYMENT="$model_name" \
        uv run examples/langchain_agent.py

    run_example_case "pydanticai_agent" "$model_name :: pydanticai_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/pydanticai_agent.py

    run_example_case "pydanticai_agent" "$model_name :: pydanticai_agent (claude)" \
        env FOUNDRY_ANTHROPIC_DEPLOYMENT="$model_name" \
        uv run examples/pydanticai_agent.py
}

for model_name in "${MODELS[@]}"; do
    run_for_model "$model_name"
done

echo
echo "========================================"
echo "Manual test summary"
echo "PASS: $PASS_COUNT"
echo "FAIL: $FAIL_COUNT"
echo "========================================"

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi