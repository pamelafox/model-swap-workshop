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
    "gpt-5.5"
)

EXAMPLES=(
    "openai_responses"
    "entity_extraction"
    "anthropic_messages"
    "agentframework_agent"
    "agentframework_workflow"
    "langgraph_workflow"
    "langchain_agent"
    "litellm_swap"
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

    run_example_case "openai_responses" "$model_name :: openai_responses" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/openai_responses.py

    run_example_case "entity_extraction" "$model_name :: entity_extraction" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/entity_extraction.py

    run_example_case "anthropic_messages" "$model_name :: anthropic_messages" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/anthropic_messages.py

    run_example_case "agentframework_agent" "$model_name :: agentframework_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_agent.py

    run_example_case "agentframework_agent" "$model_name :: agentframework_agent (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_agent.py

    run_example_case "agentframework_workflow" "$model_name :: agentframework_workflow (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_workflow.py

    run_example_case "agentframework_workflow" "$model_name :: agentframework_workflow (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/agentframework_workflow.py

    run_example_case "langgraph_workflow" "$model_name :: langgraph_workflow (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/langgraph_workflow.py

    run_example_case "langgraph_workflow" "$model_name :: langgraph_workflow (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/langgraph_workflow.py

    run_example_case "langchain_agent" "$model_name :: langchain_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/langchain_agent.py

    run_example_case "langchain_agent" "$model_name :: langchain_agent (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/langchain_agent.py

    run_example_case "litellm_swap" "$model_name :: litellm_swap (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/litellm_swap.py

    run_example_case "litellm_swap" "$model_name :: litellm_swap (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
        uv run examples/litellm_swap.py

    run_example_case "pydanticai_agent" "$model_name :: pydanticai_agent (openai)" \
        env FOUNDRY_OPENAI_DEPLOYMENT="$model_name" \
        uv run examples/pydanticai_agent.py

    run_example_case "pydanticai_agent" "$model_name :: pydanticai_agent (claude)" \
        env FOUNDRY_CLAUDE_DEPLOYMENT="$model_name" \
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