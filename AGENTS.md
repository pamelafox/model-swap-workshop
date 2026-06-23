# Instructions for coding agents

This repo is for the following workshop:

## Model Swap Workshop

Frontier labs are releasing new models constantly, and it is hard to know when "better" is better enough to justify touching a working system. On top of that, "just swap the model" often turns into real work because providers expose different APIs and different expectations around tools and structured outputs.

The model swap workshop is a hands-on bake-off across frontier LLMs. We run the same scenarios using multiple models (OpenAI, Anthropic, Kimi, and more) and compare results side by side for agentic tool use, structured outputs, and multimodal tasks.

Swapping models is not just changing a model name. In this workshop, you actually do the swaps, including moving between OpenAI-style Responses APIs and Anthropic-style Messages APIs, then see what breaks and what needs to change in prompts, tool definitions, and JSON strategies.

The workshop finishes by running a small eval suite so you can quantify tradeoffs instead of relying on vibes. We provide the Microsoft Foundry environment for access to models, no account needed.

### Outline

* Introducing our models - comparison table - Kimi, DeepSeek, Mistral, GPT-5.5, Sonnet
* Single LLM calls (with optional parameters like temperature, reasoning effort)
  * [`single_llm_letter_counting.py`](examples/single_llm_letter_counting.py) — character-level counting
  * [`single_llm_spatial_reasoning.py`](examples/single_llm_spatial_reasoning.py) — multi-step rotation tracking
  * [`single_llm_self_calibration.py`](examples/single_llm_self_calibration.py) — confidence estimation
  * [`single_llm_multi_constraint.py`](examples/single_llm_multi_constraint.py) — acrostic + word count + format
* What are the knobs we can change? Prompt, parameters
* RAG: LLM call with answer grounded in citations
    * How do we get good citations?
    * Most models: Ask for them in a certain format
      * [`rag_responses.py`](examples/rag_responses.py) — OpenAI Responses API with prompt-based citations
    * Anthropic: Use citations feature
      * [`rag_messages.py`](examples/rag_messages.py) — Anthropic Messages API with built-in citations feature
* Tool calling: Can the LLMs call tools... with the right arguments?
  * [`function_calling.py`](examples/function_calling.py) — single tool, relative date resolution
  * [`function_calling_code.py`](examples/function_calling_code.py) — code execution tool (Monty sandbox)
* Tool call selection from multiple tools
  * [`function_calling_loop.py`](examples/function_calling_loop.py) — weather + movies tools, multi-turn loop
* Structured outputs: Adhere to the schema
  * [`structured_outputs.py`](examples/structured_outputs.py) — FlightBooking schema extraction
  * Only some models support strict structured outputs, fallback to tool calling otherwise
* Image/multimodal input
  * [`image_input.py`](examples/image_input.py) — vision capabilities across models
* Agent loops: How do models handle repeated tool calls over time?
  * [`function_calling_loop.py`](examples/function_calling_loop.py) — multi-turn agent conversation
  * [`pydanticai_agent.py`](examples/pydanticai_agent.py) — PydanticAI agent with typed tools
  * [`langchain_agent.py`](examples/langchain_agent.py) — LangChain agent with OpenAI/Anthropic
  * [`agentframework_agent.py`](examples/agentframework_agent.py) — Microsoft Agent Framework
* Evaluations: Quantify tradeoffs instead of vibes
  * [`evals_basic.py`](examples/evals_basic.py) — programmatic checks (exact match, schema validation)
  * [`evals_foundry_judge.py`](examples/evals_foundry_judge.py) — LLM judge with azure-ai-evaluation (GroundednessEvaluator)
  * [`evals_agent.py`](examples/evals_agent.py) — agent eval with ToolCallAccuracyEvaluator
  * [`evals_foundry_project.py`](examples/evals_foundry_project.py) — openai.evals.create via Foundry project (optional, requires project)

## Single LLM call results across models

Each example uses the OpenAI Responses API via Foundry. Results below are representative (non-deterministic models may vary between runs).

| Example | gpt-5.5 | Kimi-K2.6 | Mistral-Large-3 | DeepSeek-V4-Flash |
|---------|---------|-----------|-----------------|-------------------|
| **Letter counting** (`single_llm_letter_counting.py`) — count "e" in a sentence (correct: 13) | 13 ✅ | 13 ✅ | 8–10 ❌ | 6 ❌ |
| **Spatial reasoning** (`single_llm_spatial_reasoning.py`) — multi-step rotation (correct: Southeast) | Southeast ✅ | Southeast ✅ | Northeast ❌ | West ❌ |
| **Self-calibration** (`single_llm_self_calibration.py`) — confidence rating (lower = more honest) | 65 | 55 | 85 | 85 |
| **Multi-constraint** (`single_llm_multi_constraint.py`) — acrostic + word count + format | ✅ all constraints | ✅ all constraints | ❌ fails word count | ✅ all constraints |

## RAG results across models

The RAG example (`rag_responses.py`) asks "what are the key differences between how honey bees and carpenter bees build their nests?" but the retrieved sources only contain carpenter bee nesting info — honey bee nest construction is NOT in the sources. This tests whether models stay grounded or hallucinate.

| Model | Grounding behavior |
|-------|-------------------|
| **gpt-5.5** | ✅ Correctly states honey bee nest-building is "not described in the provided material" |
| **Kimi-K2.6** | ✅ Correctly states "sources do not include further details on how honey bees construct their hives" |
| **DeepSeek-V4-Flash** | ✅ Correctly states "key differences… are not available" from sources |
| **Mistral-Large-3** | ❌ Hallucinates honey bee details (wax combs, hexagonal cells, secreted beeswax) not present in sources |
| **claude-sonnet-4-5** | ✅ Correctly states "documents do not contain information about how honey bees construct their nests" |

The Anthropic version (`rag_messages.py`) uses Claude's built-in citations feature instead of prompt-based citation instructions.

## Tool calling results across models

The tool calling example (`function_calling.py`) provides a single `book_flight` tool and asks the model to book a flight using relative dates: "departing next Tuesday and returning the following Monday" (with today = Sunday June 15, 2026 given in the system prompt). The correct dates are June 17 (Tuesday) and June 23 (Monday). This tests whether models can resolve relative dates to correct calendar dates.

| Model | Departure date | Return date | Analysis |
|-------|---------------|-------------|----------|
| **gpt-5.5** | — | — | Asks which Tokyo airport (HND or NRT) instead of making assumptions |
| **Kimi-K2.6** | 2026-06-17 (Tue) ✅ | 2026-06-23 (Mon) ✅ | Correct relative date resolution |
| **Mistral-Large-3** | 2026-06-24 (Tue) | 2026-06-30 (Mon) | Interprets "next Tuesday" as next week's Tuesday — debatable but internally consistent |
| **DeepSeek-V4-Flash** | 2026-06-17 (Tue) ✅ | 2026-06-22 (Sun) ❌ | Wrong return day of the week (off by one day) |

## Structured outputs results across models

The structured outputs example (`structured_outputs.py`) asks models to extract a `FlightBooking` schema (with enums for trip type and cabin class) from a casual message with relative dates. Same date challenge as tool calling — "next Tuesday" / "that Monday" — plus schema adherence (should return IATA airport codes, not city names).

| Model | origin_airport | destination_airport | departure | return | Schema adherence |
|-------|---------------|--------------------:|-----------|--------|-----------------|
| **gpt-5.5** | SFO ✅ | "Tokyo" ❌ | 2026-06-17 ✅ | 2026-06-23 ✅ | City name instead of IATA code for destination |
| **Kimi-K2.6** | SFO ✅ | NRT ✅ | 2026-06-17 ✅ | 2026-06-23 ✅ | All fields correct |
| **Mistral-Large-3** | SFO ✅ | NRT ✅ | 2026-06-23 | 2026-06-29 | Same "next week" date interpretation as tool calling |
| **DeepSeek-V4-Flash** | "San Francisco" ❌ | "Tokyo" ❌ | 2026-06-16 ❌ | 2026-06-22 ❌ | City names instead of codes, wrong dates |

GPT models use `responses.parse()` with strict `text_format` (enforced schema). Other models fall back to function calling with `tool_choice="required"` since they don't enforce structured output schemas.

## Code execution results across models

The code execution example (`function_calling_code.py`) gives models an `execute_python` tool (using the Monty sandbox) and asks them to count the letter "e" in a sentence (correct answer: 13). This is the same task that models struggled with in the single LLM examples — Mistral got 8–10, DeepSeek got 6. With a code tool, all models get 13 ✅, but efficiency varies wildly.

| Model | Tool calls | Behavior |
|-------|-----------|----------|
| **gpt-5.5** | 1 | Clean single-shot solution |
| **Mistral-Large-3** | 1 | Clean single-shot solution |
| **Kimi-K2.6** | 2 | Verbose code with word-by-word breakdown, retries because `print()` returns `None` |
| **DeepSeek-V4-Flash** | 8 | Keeps retrying because `print()` returns `None` — can't figure out to return an expression |

## Samples in this repo

All examples authenticate to Foundry using an API key and reference environment variables from a `.env` file.

Key SDKs/frameworks used:
- **OpenAI Python SDK** (`openai`): For calling Foundry-hosted OpenAI models via the Responses API.
- **Anthropic Python SDK** (`anthropic`): For calling Foundry-hosted Claude models via the Messages API.
- **LiteLLM** (`litellm`): A unified interface that abstracts provider differences.
- **PydanticAI** (`pydantic-ai`): Agent framework with typed tool support, works with OpenAI or Anthropic providers.
- **LangChain** (`langchain`, `langchain-anthropic`, `langchain-azure-ai`): Agent framework using `ChatAnthropic` for Claude via Messages API and `AzureAIOpenAIApiChatModel` for OpenAI via Responses API.
- **Microsoft Agent Framework** (`agent-framework-*`): Microsoft's agent framework, supporting OpenAI and Anthropic clients.

The Microsoft Agent Framework (MAF) GitHub repo is here:
https://github.com/microsoft/agent-framework
The Python changelog is here:
https://github.com/microsoft/agent-framework/blob/main/python/CHANGELOG.md
MAF documentation: https://learn.microsoft.com/agent-framework/

## Open issues affecting these samples

- Anthropic SDK bearer-token callable support: https://github.com/anthropics/anthropic-sdk-python/issues/1496#issuecomment-4685322526
    This affects Foundry auth ergonomics for Anthropic-based samples because the SDK currently expects a sync `AccessTokenProvider` instead of a simpler bearer-token callback shape.
- LangChain Azure Anthropic Messages API support: https://github.com/langchain-ai/langchain-azure/issues/673
    This affects whether Claude via Foundry can be handled through `langchain-azure-ai` instead of mixing `langchain-anthropic` with Foundry-specific configuration.
- MAF Anthropic workflow assistant-message compatibility fix: https://github.com/microsoft/agent-framework/pull/6207
    This affects multi-agent workflow chaining with Anthropic, where assistant-role messages may need re-roling to user until the upstream fix is available in a released version.
- OpenAI SDK `DEFER_PYDANTIC_BUILD` / `MockValSer` crash: https://github.com/openai/openai-python/issues/1306
    The SDK defers pydantic model builds by default to speed up imports. When it then uses `model_construct()` to build response objects (bypassing validation), calling `model_dump()` on those objects crashes with `TypeError: 'MockValSer' object is not an instance of 'SchemaSerializer'`. Workaround: set `DEFER_PYDANTIC_BUILD=0` before importing openai. Examples that use `responses.parse()` do this via `os.environ.setdefault("DEFER_PYDANTIC_BUILD", "0")` at the top of the file.
- OpenAI SDK `responses.parse()` `PydanticSerializationUnexpectedValue` warnings: https://github.com/openai/openai-python/issues/2872
    When calling `responses.parse()`, pydantic emits a flood of `PydanticSerializationUnexpectedValue` warnings because the SDK's `output` field is a large union and pydantic tries every variant when serializing. The warnings are non-fatal and the parsed result is correct. A fix PR (#2885) using `SerializeAsAny` has been open since February but not yet merged. Workaround: suppress with `warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)`.

## Interesting model differences

- **Kimi**: Always starts response content with a reasoning item (e.g. `{'type': 'reasoning', ...}`) before the text item. Code that assumes `content[0]` is the text block will break.
- **gpt-5.5**: Does not support `temperature` parameter (returns 400 error). Use `reasoning.effort` instead.
- **DeepSeek-V4-Flash / DeepSeek-V4-Pro**: Do not enforce strict structured outputs. When using `responses.parse()` with `text_format`, the model may return prose instead of JSON, or return JSON with invented field names that don't match the schema (e.g. `issue_type` instead of `type`). Simple schemas (like `CalendarEvent`) may work by luck, but complex schemas with enums or non-obvious field names fail. These models also do not support image/vision inputs (returns 400 error via Responses API). Via Chat Completions API, they silently accept image payloads but do not actually process the image pixels — DeepSeek-V4-Flash admits it cannot see images, while DeepSeek-V4-Pro confidently hallucinate descriptions based on the text prompt alone.
- **Kimi-K2.6**: Supports image/vision inputs via Chat Completions API, but only with inline base64-encoded data URIs. Remote image URLs return a 400 error. Via Responses API, all image inputs are rejected.
- **Anthropic on Foundry**: URL-based image sources (`"type": "url"`) in the Messages API return "Unable to download the file" error. Use base64-encoded images instead. This appears to be a Foundry-specific limitation — the same URL sources work against the Anthropic API directly.

## TODOs

- [x] Check for temperature support across the models
- [x] Try chat completions with image input for other models 
- [x] Try multilingual scenarios since models differ in their language support
    Tested translation, cross-lingual instruction following (Chinese→Spanish), and idiomatic translation.
    All four models handle multilingual well — no meaningful correctness variance found.
- [x] Try code execution (with monty, maybe with tool calling)
- [x] Add evals

## Package management

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Use `uv` commands instead of `pip`:

```bash
uv add <package>
uv sync
```

## Manual test plan

Run the repo-root test script:

```bash
./manual_test.sh
```

Keep `manual_test.sh` up to date whenever you add a new sample or add support for another model path in an existing sample.

## Debugging Azure Python SDK HTTP requests

When debugging HTTP interactions between Azure Python SDKs (like `azure-ai-evaluation`) and Azure services, there are three levels of logging you can enable:

### 1. Azure SDK logger (request headers and URLs)

Set the Azure SDK loggers to DEBUG level to see request URLs, headers, and status codes:

```python
import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("azure").setLevel(logging.DEBUG)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.DEBUG)
```

### 2. Raw HTTP wire data (request/response headers)

Enable `http.client` debug logging to see the raw HTTP wire protocol, including request and response headers:

```python
import http.client
http.client.HTTPConnection.debuglevel = 1
```

Note: Response bodies will typically not be visible at this level because Azure SDKs use gzip compression, and `http.client` logs the raw compressed bytes.

### 3. Decompressed response bodies

To see actual response bodies, monkey-patch the Azure SDK's `HttpLoggingPolicy.on_response` method. This works because `response.http_response.body()` returns the decompressed content:

```python
from azure.core.pipeline.policies import HttpLoggingPolicy

_original_on_response = HttpLoggingPolicy.on_response

def _on_response_with_body(self, request, response):
    _original_on_response(self, request, response)
    try:
        body = response.http_response.body()
        if body:
            _logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
            _logger.debug("Response body: %s", body[:4096].decode("utf-8", errors="replace"))
    except Exception:
        pass

HttpLoggingPolicy.on_response = _on_response_with_body
```
