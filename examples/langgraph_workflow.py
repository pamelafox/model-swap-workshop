import asyncio
import json
import os
import warnings
from typing import Annotated, Any, TypedDict

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

load_dotenv(override=True)
warnings.filterwarnings("ignore", message="Pydantic serializer warnings:*")

azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])

provider = os.environ.get("MODEL_CHOICE", "claude")


class ReviewResult(BaseModel):
    """Review evaluation with scores and feedback."""

    score: int
    feedback: str
    clarity: int
    completeness: int
    accuracy: int
    structure: int


def build_model() -> Any:
    if provider == "openai":
        return AzureAIOpenAIApiChatModel(
            endpoint=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1",
            credential=azure_credential,
            model=os.environ["FOUNDRY_OPENAI_DEPLOYMENT"],
            use_responses_api=True,
        )
    if provider == "claude":
        token_provider = get_bearer_token_provider(azure_credential, "https://ai.azure.com/.default")
        return ChatAnthropic(
            model=os.environ["FOUNDRY_CLAUDE_DEPLOYMENT"],
            base_url=os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/anthropic",
            api_key="placeholder",
            default_headers={"Authorization": f"Bearer {token_provider()}"},
        )
    raise ValueError(f"Unsupported MODEL_CHOICE value: {provider}")


model = build_model()
if provider == "openai":
    review_model = model.with_structured_output(ReviewResult, method="json_schema")
else:
    review_model = model.with_structured_output(ReviewResult, method="function_calling")


class WorkflowState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    review: dict[str, Any]


def latest_message_text(state: WorkflowState) -> str:
    for message in reversed(state["messages"]):
        content = message_to_text(message)
        if content.strip():
            return content
    return ""


def message_to_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text", "")))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


def parse_review_text(text: str) -> ReviewResult:
    cleaned_text = text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]
    return parse_review_payload(json.loads(cleaned_text.strip()))


def parse_review_payload(payload: Any) -> ReviewResult:
    if isinstance(payload, ReviewResult):
        return payload
    if not isinstance(payload, dict):
        raise TypeError(f"Unsupported review payload type: {type(payload)!r}")

    direct_fields = {"score", "feedback", "clarity", "completeness", "accuracy", "structure"}
    if direct_fields.issubset(payload.keys()) and all(isinstance(payload[field], int) for field in direct_fields - {"feedback"}):
        return ReviewResult.model_validate(payload)

    def collect_scores(value: Any, scores: list[int]) -> None:
        if isinstance(value, dict):
            score = value.get("score")
            if isinstance(score, (int, float)):
                scores.append(int(score))
            for item in value.values():
                collect_scores(item, scores)
        elif isinstance(value, list):
            for item in value:
                collect_scores(item, scores)

    def collect_notes(value: Any, notes: list[str]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"feedback", "summary"} and isinstance(item, str) and item.strip():
                    notes.append(item.strip())
                elif key in {"issues", "strengths"} and isinstance(item, list):
                    notes.extend(str(entry).strip() for entry in item if str(entry).strip())
                else:
                    collect_notes(item, notes)
        elif isinstance(value, list):
            for item in value:
                collect_notes(item, notes)

    category_scores: list[int] = []
    notes: list[str] = []
    collect_scores(payload, category_scores)
    collect_notes(payload, notes)

    overall_score = round(sum(category_scores) / len(category_scores)) if category_scores else 0
    feedback = payload.get("feedback")
    if not isinstance(feedback, str) or not feedback.strip():
        feedback = "; ".join(notes[:4]) or "Review completed."

    return ReviewResult(
        score=overall_score,
        feedback=feedback,
        clarity=category_scores[0] if len(category_scores) > 0 else 0,
        completeness=category_scores[1] if len(category_scores) > 1 else 0,
        accuracy=category_scores[2] if len(category_scores) > 2 else 0,
        structure=category_scores[3] if len(category_scores) > 3 else 0,
    )


def review_from_state(state: WorkflowState) -> ReviewResult | None:
    review = state.get("review")
    if isinstance(review, dict):
        return ReviewResult.model_validate(review)
    return None


async def writer_node(state: WorkflowState) -> dict[str, list[BaseMessage]]:
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are an excellent content writer. Create clear, engaging content based on the user's request. "
                    "Focus on clarity, accuracy, and proper structure."
                )
            ),
            *state["messages"],
        ]
    )
    return {"messages": [response]}


async def reviewer_node(state: WorkflowState) -> dict[str, dict[str, Any]]:
    review = await review_model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are an expert content reviewer. Evaluate the writer's content based on clarity, "
                    "completeness, accuracy, and structure. Respond only with valid structured output."
                )
            ),
            *state["messages"],
        ]
    )
    if isinstance(review, ReviewResult):
        return {"review": review.model_dump()}
    if isinstance(review, dict):
        return {"review": review}
    return {"review": parse_review_payload(review).model_dump()}


def route_after_review(state: WorkflowState) -> str:
    review = review_from_state(state)
    if review is not None and review.score >= 80:
        return "publisher"
    return "editor"


async def editor_node(state: WorkflowState) -> dict[str, list[BaseMessage]]:
    review = review_from_state(state)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a skilled editor. Improve the content by addressing all issues mentioned in the review. "
                    "Maintain the original intent while enhancing clarity, completeness, accuracy, and structure."
                )
            ),
            HumanMessage(
                content=(
                    f"Review feedback: {review.feedback if review else 'No review available.'}\n\n"
                    f"Revise this draft:\n{latest_message_text(state)}"
                )
            ),
        ]
    )
    return {"messages": [response]}


async def publisher_node(state: WorkflowState) -> dict[str, list[BaseMessage]]:
    review = review_from_state(state)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a publishing agent. You receive approved or edited content. Format it for publication "
                    "with proper headings and structure."
                )
            ),
            HumanMessage(
                content=(
                    f"Review score: {review.score if review else 'unknown'}\n\n"
                    f"Publish this content:\n{latest_message_text(state)}"
                )
            ),
        ]
    )
    return {"messages": [response]}


async def summarizer_node(state: WorkflowState) -> dict[str, list[BaseMessage]]:
    review = review_from_state(state)
    workflow_path = "direct approval" if review is not None and review.score >= 80 else "edited"
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a summarizer agent. Create a final publication report with a brief summary of the "
                    "published content, the workflow path taken, and key highlights and takeaways. Keep it concise "
                    "and professional."
                )
            ),
            HumanMessage(
                content=(
                    f"Workflow path: {workflow_path}\n"
                    f"Review score: {review.score if review else 'unknown'}\n\n"
                    f"Published content:\n{latest_message_text(state)}"
                )
            ),
        ]
    )
    return {"messages": [response]}


builder = StateGraph(WorkflowState)
builder.add_node("writer", writer_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("editor", editor_node)
builder.add_node("publisher", publisher_node)
builder.add_node("summarizer", summarizer_node)

builder.add_edge(START, "writer")
builder.add_edge("writer", "reviewer")
builder.add_conditional_edges("reviewer", route_after_review, {"publisher": "publisher", "editor": "editor"})
builder.add_edge("editor", "publisher")
builder.add_edge("publisher", "summarizer")
builder.add_edge("summarizer", END)

workflow = builder.compile(name="Content Review Workflow")


async def main() -> None:
    result = await workflow.ainvoke(
        {"messages": [HumanMessage(content="Write a short bullet-point list of Anthropic vs OpenAI models")]}
    )
    outputs = result.get("messages", [])
    if not outputs:
        print("No workflow output was produced.")
        return

    last_output = outputs[-1]
    print(message_to_text(last_output))


if __name__ == "__main__":
    asyncio.run(main())