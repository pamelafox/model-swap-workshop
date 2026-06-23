# Model Swap Workshop

Welcome! In this workshop you'll run the same scenarios across multiple frontier LLMs, observe where they differ, then tweak prompts and tool definitions to improve results. At the end, you'll quantify the tradeoffs with an eval suite.

### Table of contents

1. [Install the prerequisites](#install-the-prerequisites)
2. [Setup the environment](#setup-the-environment)
3. [Part 1: Single LLM calls](#part-1-single-llm-calls)
4. [Part 2: RAG](#part-2-rag)
5. [Part 3: Tool calling](#part-3-tool-calling)
6. [Part 4: Structured outputs](#part-4-structured-outputs)
7. [Part 5: Code execution](#part-5-code-execution)
8. [Part 6: Agent loops](#part-6-agent-loops)
9. [Part 7: Evaluations](#part-7-evaluations)
10. [Recap](#recap)

## Install the prerequisites

1. **Python 3.10+**: Check with `python --version`. Install from [python.org](https://www.python.org/downloads/) if needed.

2. **uv** (Python package manager): Install with:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Or on macOS: `brew install uv`

3. **Install dependencies**: From the repo root, run:

   ```bash
   uv sync
   ```

   This creates a `.venv` and installs all packages from `pyproject.toml`.

## Setup the environment

Make sure you have a `.env` file with Foundry credentials (see `.env.sample`). Since some Azure accounts aren't able to access Anthropic models, there are separate environment variables to configure the Foundry project for use with those models.

```shell
FOUNDRY_MODELS_ENDPOINT=https://YOUR-ACCOUNT.services.ai.azure.com
FOUNDRY_API_KEY=YOUR-FOUNDRY-API-KEY

FOUNDRY_ANTHROPIC_MODELS_ENDPOINT=https://YOUR-ACCOUNT.services.ai.azure.com
FOUNDRY_ANTHROPIC_API_KEY=YOUR-FOUNDRY-ANTHROPIC-API-KEY
```

The Python files assume that the following Foundry models are deployed, with the deployment names matching the model names:

* "gpt-5.5"
* "Mistral-Large-3"
* "Kimi-K2.6"
* "DeepSeek-V4-Flash"
* "claude-sonnet-4-5" (for Anthropic examples only)

Each file makes it easy to switch between different models.

All examples run with:

```bash
uv run examples/<filename>.py
```

---

## Part 1: Single LLM calls

These examples test raw LLM capabilities with a single prompt — no tools, no context.

### Run it

1. Open [examples/single_llm_letter_counting.py](examples/single_llm_letter_counting.py)
2. Run the file:

    ```bash
    uv run examples/single_llm_letter_counting.py
    ```

3. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file. In our trials, only some models got the answer correctly (13), while other models returned the wrong answer.

### Exercise: Improve the output

Open [examples/single_llm_letter_counting.py](examples/single_llm_letter_counting.py) and find the `PROMPT` variable. Can you modify it so that **Mistral** or **DeepSeek** gets the correct answer (13)?

Ideas to try:
- Ask the model to list each occurrence of "e" before counting
- Break the sentence into individual words and ask it to count per-word
- Add "Think step by step" or chain-of-thought instructions
- Tell it to double-check its answer
- Tweak parameters like `temperature` or `reasoning.effort`


### Try other examples

We've included other examples of single LLM calls where the output varies based on the model used. 

    * [examples/single_llm_spatial_reasoning.py](examples/single_llm_spatial_reasoning.py): We check the LLM's spatial reasoning ability by describing a series of turns, and then asking "Which direction am I facing after these turns?". 
    * [examples/single_llm_multi_constraint.py](examples/single_llm_multi_constraint.py): We ask the LLM to write a poem that satisfies multiple rules about start letters and number of words.
    * [examples/single_llm_self_calibration.py](examples/single_llm_self_calibration.py): We ask the LLM a question that should not be directly answerable from the weights, and then ask it, "How confident are you in your answer?". Generally, the best models report low confidence.

When you find an example that fails for a particular model, try rewriting the prompt or tweaking parameters to improve the output.

---

## Part 2: RAG

### Run it

1. Open [examples/rag_responses.py](examples/rag_responses.py)
2. Set `MODEL = "gpt-5.5"` and run: `uv run examples/rag_responses.py`
3. Change to `MODEL = "Mistral-Large-3"` and run again

The question asks about honey bees AND carpenter bees, but the sources only contain carpenter bee info. Watch which models hallucinate honey bee facts.

### What to observe

- **gpt-5.5, Kimi, DeepSeek**: Correctly say "honey bee info not in sources"
- **Mistral**: Hallucinates honey bee details (wax combs, hexagonal cells)

### Exercise: Fix the hallucination

Open [examples/rag_responses.py](examples/rag_responses.py) and find the `SYSTEM_MESSAGE`. Can you strengthen the grounding instructions so that Mistral stops hallucinating?

Ideas to try:
- Add explicit instructions like "If information is not in the sources, say so clearly"
- Add "NEVER make up information that isn't in the provided sources"
- Use a structured format: "For each claim, cite the source ID or state 'not in sources'"
- Add a negative example: "Do NOT mention facts about honey bees unless they appear in the sources"

### Bonus: Anthropic citations

Run [examples/rag_messages.py](examples/rag_messages.py) to see how Claude's built-in citations feature works differently from prompt-based citations. Notice how the API response includes structured citation objects rather than relying on the model to format them.

---

## Part 3: Tool calling

### Run it

1. Open [examples/function_calling.py](examples/function_calling.py)
2. Set `MODEL = "gpt-5.5"` and run: `uv run examples/function_calling.py`
3. Swap through `"Kimi-K2.6"`, `"Mistral-Large-3"`, and `"DeepSeek-V4-Flash"`

The model must resolve "next Tuesday" and "the following Monday" relative to "today is Sunday, June 15, 2026."

### What to observe

- **Kimi**: Correct dates (June 17, June 23)
- **Mistral**: Interprets "next Tuesday" as the following week (June 24)
- **DeepSeek**: Gets departure right but return is off by one day
- **gpt-5.5**: May ask clarifying questions instead of booking

### Exercise: Make date resolution reliable

Open [examples/function_calling.py](examples/function_calling.py). Can you get ALL models to produce the correct dates?

Ideas to try:
- Change the system prompt to include the explicit calendar: "Today is Sunday June 15. This week: Mon 16, Tue 17, Wed 18... Next week: Mon 23..."
- Add date examples in the tool parameter descriptions: `"Departure date in YYYY-MM-DD format, e.g. 2026-06-17 for Tuesday June 17"`
- Rephrase the user message to use absolute dates instead of relative ones
- Add `"Today's date: 2026-06-15 (Sunday)"` directly in the user message

Which approach works across the most models?

---

## Part 4: Structured outputs

### Run it

1. Open [examples/structured_outputs.py](examples/structured_outputs.py)
2. Set `MODEL = "gpt-5.5"` and run: `uv run examples/structured_outputs.py`
3. Swap through `"Kimi-K2.6"` and `"DeepSeek-V4-Flash"`

### What to observe

- **gpt-5.5**: Uses `responses.parse()` with strict schema enforcement — but still writes "Tokyo" instead of an IATA code
- **Kimi**: All fields correct via tool-calling fallback
- **DeepSeek**: Returns city names instead of IATA codes, wrong dates

### Exercise: Improve schema adherence

Open [examples/structured_outputs.py](examples/structured_outputs.py). Can you get DeepSeek to return proper IATA codes?

Ideas to try:
- Make the field descriptions more explicit: `"3-letter IATA airport code (e.g. SFO, NRT, HND). Must be exactly 3 uppercase letters."`
- Add examples in the system prompt: "Example: San Francisco → SFO, Tokyo Narita → NRT"
- Add a `pattern` constraint to the JSON schema: `"pattern": "^[A-Z]{3}$"`
- For non-GPT models, try adding `"enum"` with common airport codes

---

## Part 5: Code execution

### Run it

1. Open [examples/function_calling_code.py](examples/function_calling_code.py)
2. Set `MODEL = "gpt-5.5"` and run: `uv run examples/function_calling_code.py`
3. Change to `MODEL = "DeepSeek-V4-Flash"` and run again

### What to observe

This gives models an `execute_python` tool for the same letter-counting task. All models now get 13 ✅ — but some take 8 retries because `print()` returns `None` and they can't figure out to use a bare expression.

- **gpt-5.5, Mistral**: 1 call, clean solution
- **DeepSeek**: Up to 8 retries

### Discussion

When should you give a model a code tool vs. engineering the prompt? What are the cost/latency tradeoffs of multiple tool calls?

---

## Part 6: Agent loops

### Run it

Try one or more agent frameworks — open the file, set your model, and run:

- [examples/pydanticai_agent.py](examples/pydanticai_agent.py): `uv run examples/pydanticai_agent.py`
- [examples/langchain_agent.py](examples/langchain_agent.py): `uv run examples/langchain_agent.py`
- [examples/agentframework_agent.py](examples/agentframework_agent.py): `uv run examples/agentframework_agent.py`

These run multi-turn conversations with tool use. The [examples/function_calling_loop.py](examples/function_calling_loop.py) example shows the raw loop without a framework.

### What to observe

- How does each framework abstract the tool call → result → next message loop?
- What happens when you swap the model inside a framework — does it just work or do you need to change configuration?

---

## Part 7: Evaluations

Now quantify what you observed.

### 7a: Basic programmatic evals

```bash
uv run examples/evals_basic.py
```

This runs all four test cases (letter counting, spatial reasoning, structured outputs, tool calling) across all models and checks against ground truth. No LLM judge needed — just exact match and schema validation.

### 7b: LLM judge (GroundednessEvaluator)

```bash
uv run examples/evals_foundry_judge.py
```

Uses `azure-ai-evaluation` with `GroundednessEvaluator` to score the RAG outputs. The judge (gpt-5.5) evaluates whether each model's response is grounded in the provided sources.

### 7c: Agent eval (ToolCallAccuracyEvaluator)

```bash
uv run examples/evals_agent.py
```

Uses `ToolCallAccuracyEvaluator` to score whether models made correct tool calls with correct arguments, given the system prompt context.

### 7d: Foundry project evals (optional)

```bash
uv run examples/evals_foundry_project.py
```

Uses `openai.evals.create` to run evals server-side via a Foundry project. Results are viewable in the Foundry portal. **Requires `FOUNDRY_PROJECT_ENDPOINT` env var.**

### Discussion

- Where do the basic evals and LLM judge disagree? Why?
- The LLM judge can be non-deterministic — run `evals_agent.py` twice and compare scores
- When would you use each approach in production?

---

## Recap

| What we tested | Winner(s) | What helps weaker models |
|----------------|-----------|--------------------------|
| Raw reasoning (counting, spatial) | gpt-5.5, Kimi | Chain-of-thought prompts, code tools |
| Grounding / hallucination | gpt-5.5, Kimi, DeepSeek | Stronger system prompt instructions |
| Date resolution in tools | Kimi | Explicit calendar in prompt, absolute dates |
| Schema adherence | Kimi (via tool calling) | Better field descriptions, examples |
| Code tool efficiency | gpt-5.5, Mistral | Clearer tool description about return values |

**Key takeaway**: "Just swap the model" is never just swapping the model. Prompts, tool definitions, and output strategies all need tuning per model. Evals let you quantify instead of guessing.
