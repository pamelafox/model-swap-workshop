#!/bin/bash

set -euo pipefail

azure_tenant_id="$(azd env get-value AZURE_TENANT_ID)"
foundry_models_endpoint="$(azd env get-value FOUNDRY_MODELS_ENDPOINT)"
foundry_openai_deployment="$(azd env get-value FOUNDRY_OPENAI_DEPLOYMENT)"
foundry_claude_deployment="$(azd env get-value FOUNDRY_CLAUDE_DEPLOYMENT)"

{
	echo "AZURE_TENANT_ID=$azure_tenant_id"
	echo
	echo "FOUNDRY_MODELS_ENDPOINT=$foundry_models_endpoint"
	echo "FOUNDRY_OPENAI_DEPLOYMENT=$foundry_openai_deployment"
	echo "FOUNDRY_CLAUDE_DEPLOYMENT=$foundry_claude_deployment"
} > .env
