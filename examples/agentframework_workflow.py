import asyncio
import os
import sys
from typing import Any

from agent_framework import AgentExecutor, AgentExecutorResponse, Message, WorkflowBuilder
from agent_framework_openai import OpenAIChatClient
from agent_framework.anthropic import AnthropicClient
from anthropic import AsyncAnthropic
from anthropic.lib.credentials import AccessToken
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)

azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])


def _entra_credentials_provider(scope: str = "https://ai.azure.com/.default"):
    credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
    def _provider(*, force_refresh: bool = False) -> AccessToken:
        token = credential.get_token(scope)
        return AccessToken(token=token.token, expires_at=token.expires_on)
    return _provider


provider = os.environ.get("MODEL_CHOICE", "claude")
if provider == "openai":
    client = OpenAIChatClient(
        model=os.environ["FOUNDRY_OPENAI_DEPLOYMENT"],
        azure_endpoint=os.environ["FOUNDRY_MODELS_ENDPOINT"],
        credential=azure_credential,
    )
elif provider == "claude":
    client = AnthropicClient(
        model=os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"],
        anthropic_client=AsyncAnthropic(
            credentials=_entra_credentials_provider(),
            base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic",
        ),
    )


def anthropic_safe_context(messages: list[Message]) -> list[Message]:
    """Convert assistant messages to user-role messages for Anthropic workflow chaining."""
    safe_messages: list[Message] = []
    for message in messages:
        if message.role == "assistant":
            safe_messages.append(Message(role="user", contents=message.contents))
        else:
            safe_messages.append(message)
    return safe_messages


def wrap_agent(agent: Any) -> AgentExecutor:
    """Wrap agents with context mode suitable for selected provider."""
    if provider == "claude":
        # Workaround for Anthropic workflow chaining issue:
        # https://github.com/microsoft/agent-framework/issues/5008
        return AgentExecutor(agent, context_mode="custom", context_filter=anthropic_safe_context)
    return AgentExecutor(agent, context_mode="full")


# Define structured output for review results
class ReviewResult(BaseModel):
    """Review evaluation with scores and feedback."""

    score: int  # Overall quality score (0-100)
    feedback: str  # Concise, actionable feedback
    clarity: int  # Clarity score (0-100)
    completeness: int  # Completeness score (0-100)
    accuracy: int  # Accuracy score (0-100)
    structure: int  # Structure score (0-100)


# Condition function: route to editor if score < 80
def needs_editing(message: Any) -> bool:
    """Check if content needs editing based on review score."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    try:
        review = ReviewResult.model_validate_json(message.agent_response.text)
        return review.score < 80
    except Exception:
        return False


# Condition function: content is approved (score >= 80)
def is_approved(message: Any) -> bool:
    """Check if content is approved (high quality)."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    try:
        review = ReviewResult.model_validate_json(message.agent_response.text)
        return review.score >= 80
    except Exception:
        return True


# Create Writer agent - generates content
def create_writer():
    return client.as_agent(
        name="Writer",
        instructions=(
            "You are an excellent content writer. "
            "Create clear, engaging content based on the user's request. "
            "Focus on clarity, accuracy, and proper structure."
        ),
    )


# Create Reviewer agent - evaluates and provides structured feedback
def create_reviewer():
    return client.as_agent(
        name="Reviewer",
        instructions=(
            "You are an expert content reviewer. "
            "Evaluate the writer's content based on clarity, completeness, accuracy, and structure. "
            "Respond ONLY with valid JSON (no other text) in this format: "
            '{"score": <0-100>, "feedback": "<feedback>", "clarity": <0-100>, "completeness": <0-100>, "accuracy": <0-100>, "structure": <0-100>}'
        ),
    )


# Create Editor agent - improves content based on feedback
def create_editor():
    return client.as_agent(
        name="Editor",
        instructions=(
            "You are a skilled editor. You will receive content along with review feedback. "
            "Improve the content by addressing all the issues mentioned in the feedback. "
            "Maintain the original intent while enhancing clarity, completeness, accuracy, and structure."
        ),
    )


# Create Publisher agent - formats content for publication
def create_publisher():
    return client.as_agent(
        name="Publisher",
        instructions=(
            "You are a publishing agent. "
            "You receive either approved content or edited content. "
            "Format it for publication with proper headings and structure."
        ),
    )


# Create Summarizer agent - creates final publication report
def create_summarizer():
    return client.as_agent(
        name="Summarizer",
        instructions=(
            "You are a summarizer agent. Create a final publication report that includes: "
            "a brief summary of the published content, the workflow path taken (direct approval or edited), "
            "and key highlights and takeaways. Keep it concise and professional."
        ),
    )


# Build workflow with branching and convergence:
# Writer → Reviewer → [branches]:
#   - If score >= 80: → Publisher → Summarizer (direct approval path)
#   - If score < 80: → Editor → Publisher → Summarizer (improvement path)
# Both paths converge at Summarizer for final report
writer = create_writer()
reviewer = create_reviewer()
editor = create_editor()
publisher = create_publisher()
summarizer = create_summarizer()

writer_exec = wrap_agent(writer)
reviewer_exec = wrap_agent(reviewer)
editor_exec = wrap_agent(editor)
publisher_exec = wrap_agent(publisher)
summarizer_exec = wrap_agent(summarizer)

workflow = (
    WorkflowBuilder(
        name="Content Review Workflow",
        description="Multi-agent content creation with quality-based routing (Writer→Reviewer→Editor/Publisher)",
        start_executor=writer_exec,
    )
    .add_edge(writer_exec, reviewer_exec)
    # Branch 1: High quality (>= 80) goes directly to publisher
    .add_edge(reviewer_exec, publisher_exec, condition=is_approved)
    # Branch 2: Low quality (< 80) goes to editor first, then publisher
    .add_edge(reviewer_exec, editor_exec, condition=needs_editing)
    .add_edge(editor_exec, publisher_exec)
    # Both paths converge: Publisher → Summarizer
    .add_edge(publisher_exec, summarizer_exec)
    .build()
)


async def main():
    result = await workflow.run("Write a short bullet-point list of Anthropic vs OpenAI models")
    outputs = result.get_outputs()
    if not outputs:
        print("No workflow output was produced.")
        return

    last_output = outputs[-1]
    if isinstance(last_output, AgentExecutorResponse):
        print(last_output.agent_response.text)
    else:
        print(last_output)



if __name__ == "__main__":
    if "--devui" in sys.argv:
        from agent_framework.devui import serve

        serve(entities=[workflow], port=8092, auto_open=True)
    else:
        asyncio.run(main())