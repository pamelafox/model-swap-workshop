<!--
---
name: Model Swap Workshop
description: Hands-on workshop for comparing frontier models across provider APIs, tools, and structured outputs.
languages:
- python
products:
- azure-openai
- azure
- ai-services
page_type: sample
urlFragment: model-swap-workshop
---
-->
# Model Swap Workshop

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://codespaces.new/pamelafox/model-swap-workshop)
[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pamelafox/model-swap-workshop)

Frontier labs are releasing new models constantly, and it is hard to know when "better" is better enough to justify touching a working system. On top of that, "just swap the model" often turns into real work because providers expose different APIs and different expectations around tools and structured outputs.

This workshop is a hands-on bake-off across frontier LLMs. We run the same scenarios using multiple models (OpenAI, Anthropic, Kimi, and more) and compare results side by side for agentic tool use, structured outputs, and multimodal tasks.

Swapping models is not just changing a model name. In this workshop, you actually do the swaps, including moving between OpenAI-style Responses APIs and Anthropic-style Messages APIs, then see what breaks and what needs to change in prompts, tool definitions, and JSON strategies.

The workshop finishes by running a small eval suite so you can quantify tradeoffs instead of relying on vibes. We provide the Microsoft Foundry environment for access to models, no account needed.

This repository contains samples showing different Python stacks for building on top of multiple [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/) models.

* [Getting started](#getting-started)
  * [GitHub Codespaces](#github-codespaces)
  * [VS Code Dev Containers](#vs-code-dev-containers)
  * [Local environment](#local-environment)
* [Deploying Foundry models](#deploying-foundry-models)
* [Running the Python examples](#running-the-python-examples)
* [Resources](#resources)

## Getting started

You have a few options for getting started with this repository.
The quickest way to get started is GitHub Codespaces, since it will setup everything for you, but you can also [set it up locally](#local-environment).

### GitHub Codespaces

You can run this repository virtually by using GitHub Codespaces. The button will open a web-based VS Code instance in your browser:

1. Open the repository (this may take several minutes):

    [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pamelafox/python-stack-foundry-models)

2. Open a terminal window
3. Continue with the steps to run the examples

### VS Code Dev Containers

A related option is VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pamelafox/python-stack-foundry-models)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the steps to run the examples

### Local environment

1. Make sure the following tools are installed:

    * [Python 3.10+](https://www.python.org/downloads/)
    * [uv](https://docs.astral.sh/uv/getting-started/installation/)
    * Git

2. Clone the repository:

    ```shell
    git clone https://github.com/pamelafox/model-swap-workshop
    cd model-swap-workshop
    ```

3. Install the dependencies:

    ```shell
    uv sync
    ```

## Deploying Foundry models

All examples use models hosted on [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/). The project includes infrastructure as code (IaC) to provision OpenAI and Claude deployments. The IaC is defined in the `infra` directory and uses the Azure Developer CLI to provision the resources.

1. Make sure the [Azure Developer CLI (azd)](https://aka.ms/install-azd) is installed.

2. Login to Azure:

    ```shell
    azd auth login
    ```

    For GitHub Codespaces users, if the previous command fails, try:

   ```shell
    azd auth login --use-device-code
    ```

    If you are using a tenant besides the default tenant, you may need to also login with Azure CLI to that tenant:

    ```shell
    az login --tenant your-tenant-id
    ```

3. Provision the Foundry resources:

    ```shell
    azd provision
    ```

    It will prompt you to provide an `azd` environment name (like "stack-demos"), select a subscription from your Azure account, and select a location. Then it will provision the resources in your account.

4. Once the resources are provisioned, you should now see a local `.env` file with all the environment variables needed to run the scripts.
5. To delete the resources, run:

    ```shell
    azd down
    ```

## Running the Python examples

You can run the examples in this repository by executing the scripts in the `examples` directory. Each example demonstrates calling Foundry models using a different Python stack.

| Example | Description |
| ------- | ----------- |
| [openai_responses.py](examples/openai_responses.py) | Calling a Foundry-hosted OpenAI model using the OpenAI Python SDK (Responses API). |
| [entity_extraction.py](examples/entity_extraction.py) | Extracting structured event entities with Pydantic using the OpenAI Python SDK, with optional multi-model runs. |
| [anthropic_messages.py](examples/anthropic_messages.py) | Calling a Foundry-hosted Claude model using the Anthropic Python SDK (Messages API). |
| [litellm_swap.py](examples/litellm_swap.py) | Calling either OpenAI or Claude models via LiteLLM, a unified interface that abstracts provider differences. |
| [pydanticai_agent.py](examples/pydanticai_agent.py) | Building an agent with tools using PydanticAI, configured for either OpenAI or Claude on Foundry. |
| [langchain_agent.py](examples/langchain_agent.py) | Building an agent with tools using LangChain, configured for either OpenAI or Claude on Foundry. |
| [agentframework_agent.py](examples/agentframework_agent.py) | Building an agent with tools using Microsoft Agent Framework, configured for either OpenAI or Claude on Foundry. |

Run any example with:

```shell
uv run examples/<example_name>.py
```

To run the full workshop bake-off matrix across example stacks and multiple model deployments, run:

```shell
./manual_test.sh
```

## Resources

* [Microsoft Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
* [Agent Framework Documentation](https://learn.microsoft.com/agent-framework/)
* [OpenAI Python SDK](https://github.com/openai/openai-python)
* [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
* [LiteLLM](https://github.com/BerriAI/litellm)
* [PydanticAI](https://ai.pydantic.dev/)
* [LangChain](https://python.langchain.com/)
* [langchain-azure-ai](https://github.com/langchain-ai/langchain-azure)
