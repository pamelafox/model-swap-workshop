#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

run_test() {
    echo
    echo "==> $*"
    "$@"
}

run_test uv run examples/openai_responses.py
run_test uv run examples/anthropic_messages.py

run_test env MODEL_CHOICE=openai uv run examples/agentframework_agent.py
run_test env MODEL_CHOICE=claude uv run examples/agentframework_agent.py

run_test env MODEL_CHOICE=openai uv run examples/agentframework_workflow.py
run_test env MODEL_CHOICE=claude uv run examples/agentframework_workflow.py

run_test env MODEL_CHOICE=openai uv run examples/langgraph_workflow.py
run_test env MODEL_CHOICE=claude uv run examples/langgraph_workflow.py

run_test env MODEL_CHOICE=openai uv run examples/langchain_agent.py
run_test env MODEL_CHOICE=claude uv run examples/langchain_agent.py

run_test env MODEL_CHOICE=openai uv run examples/litellm_swap.py
run_test env MODEL_CHOICE=claude uv run examples/litellm_swap.py

run_test env MODEL_CHOICE=openai uv run examples/pydanticai_agent.py
run_test env MODEL_CHOICE=claude uv run examples/pydanticai_agent.py