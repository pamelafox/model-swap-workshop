# Model Swap Workshop

Welcome! In this workshop you'll run the same scenarios across multiple frontier LLMs, observe where they differ, then tweak prompts and tool definitions to improve results. At the end, you'll quantify the tradeoffs with an eval suite.

## Table of contents

1. [Install the prerequisites](#install-the-prerequisites)
2. [Setup the environment](#setup-the-environment)
3. [Part 1: Single LLM calls](#part-1-single-llm-calls)
4. [Part 2: RAG](#part-2-rag)
5. [Part 3: Image/multimodal input](#part-3-imagemultimodal-input)
6. [Part 4: Tool calling](#part-4-tool-calling)
7. [Part 5: Tool calling in a loop](#part-5-tool-calling-in-a-loop)
8. [Part 6: Agent loops](#part-6-agent-loops)
9. [Part 7: Evaluations](#part-7-evaluations)
10. [Part 8: Prompt optimization](#part-8-prompt-optimization)
11. [Recap](#recap)

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

Open [examples/single_llm_letter_counting.py](examples/single_llm_letter_counting.py) and find the `PROMPT` variable. Can you modify it so that **Mistral** or **DeepSeek** gets the correct answer?

Ideas to try:

* Ask the model to list each occurrence of "e" before counting
* Break the sentence into individual words and ask it to count per-word
* Add "Think step by step" or chain-of-thought instructions
* Tell it to double-check its answer
* Tweak `temperature` (supported on Mistral, DeepSeek, Kimi — but NOT gpt-5.5)

### Try other examples

We've included other examples of single LLM calls where the output varies based on the model used.

* [examples/single_llm_spatial_reasoning.py](examples/single_llm_spatial_reasoning.py): We check the LLM's spatial reasoning ability by describing a series of turns, and then asking "Which direction am I facing after these turns?".
* [examples/single_llm_multi_constraint.py](examples/single_llm_multi_constraint.py): We ask the LLM to write a poem that satisfies multiple rules about start letters and number of words.
* [examples/single_llm_self_calibration.py](examples/single_llm_self_calibration.py): We ask the LLM a question that should not be directly answerable from the weights, and then ask it, "How confident are you in your answer?". Generally, the best models report low confidence.

When you find an example that fails for a particular model, try rewriting the prompt or tweaking parameters to improve the output.

---

## Part 2: RAG

### Run the RAG example

1. Open [examples/rag_responses.py](examples/rag_responses.py)
2. Run the file:

    ```bash
    uv run examples/rag_responses.py
    ```

3. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file. The question asks about honey bees AND carpenter bees, but the sources only contain carpenter bee info. Observe which models still respond with information about honey bees, despite the prompt insisting that answers be grounded in sources.

#### Exercise: Improve the grounding

Set your `MODEL` to a deployment that responded with an ungrounded answer.

Open [examples/rag_responses.py](examples/rag_responses.py) and find the `SYSTEM_MESSAGE`. Can you strengthen the grounding instructions so that the model sticks to the sources?

Ideas to try:

* Add explicit instructions like "If information is not in the sources, say so clearly"
* Add "NEVER make up information that isn't in the provided sources"
* Use a structured format: "For each claim, cite the source ID or state 'not in sources'"
* Add a negative example: "Do NOT mention facts about honey bees unless they appear in the sources"

### Run the RAG example with Anthropic models

When working with the Anthropic models, we must use the Anthropic messages API, not the Responses API. That also gives us access to Claude's built-in citations feature, which outputs structured citation objects rather than relying on the model to format them.

1. Open [examples/rag_messages.py](examples/rag_messages.py)
2. Run the file:

    ```bash
    uv run examples/rag_messages.py
    ```

3. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file. Opus is the largest in the family, then Sonnet, then Haiku. Observe any differences in the output quality across the models. In our experiments, all three generated fully grounded answers. If you see otherwise, try modifying the prompt or other parameters to improve the output.

---

## Part 3: Image/multimodal input

### Run it

1. Open [examples/image_input.py](examples/image_input.py)
2. Run the file:

    ```bash
    uv run examples/image_input.py
    ```

3. The script sends 3 different images (aurochs painting, crocodile photo, plant price list) with questions that require visual understanding. Observe the accuracy and detail of each response.

4. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run.

### What to observe

* **Species identification**: Does the model correctly identify the aurochs (not a unicorn) and the crocodiles (not alligators)?
* **Data extraction**: Does the model find the actual cheapest plant in the table, or pick the wrong one?
* **Detail level**: Does the model give a one-word answer or explain its reasoning? How confident vs. hedging is it?

### Exercise: Know your model's limits

Unlike prompt or tool description issues, vision failures are fundamental capability gaps — you can't prompt your way to better eyesight. Try adding your own images to the `EXAMPLES` list and see which models handle them:

* A diagram or chart with small text
* An image with handwritten content
* A screenshot of code

Which models would you trust for a production vision task? Which would you rule out?

---

## Part 4: Tool calling

### Run it

1. Open [examples/function_calling.py](examples/function_calling.py)
2. Run the file:

    ```bash
    uv run examples/function_calling.py
    ```

3. Observe how the model normalizes the user's message into structured tool arguments. The display at the bottom compares the expected tool call output to the model's actual output.

4. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file. Observe whether the output matches the expected tool call arguments.

### Exercise: Improve tool argument quality

In our experiments, several models added "me" or "you" to attendees list, or appended "Teams" to the location. Can you get ALL models to match the expected output?

Ideas to try:

* Tighten the attendees description: `"List of attendee names only (first name or full name). Do not include the organizer."`
* Make the location description more explicit: `"Room name, or exactly 'Virtual' for online meetings. Do not include the platform name."`
* Add an example in the tool description: `"e.g. ['Sarah', 'Marcus', 'Priya']"`

Which description changes fix which models?

---

## Part 5: Tool calling in a loop

In this example, we give the model a `calculate` tool and ask a multi-step word problem. The model must decompose the problem into sequential tool calls. Models differ in how granularly they decompose — some use 4 calls, others use 7+.

### Run it

1. Open [examples/tool_loop_calculator.py](examples/tool_loop_calculator.py)
2. Run the file:

    ```bash
    uv run examples/tool_loop_calculator.py
    ```

3. Observe how many tool calls the model makes to solve the problem (expected answer: $92.28). Some models combine steps efficiently, while others decompose every sub-operation into a separate call.

4. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file. Compare the number of tool calls and the decomposition strategy.

### What to observe

* **gpt-5.5, DeepSeek, Kimi**: 4–5 calls — combine discount + subtraction into one step (e.g. `45 * 0.70`)
* **Mistral**: 7 calls — decomposes every operation separately (e.g. `45 * 0.30` then `45 - 13.5`)

### Exercise: Reduce tool calls

Choose the model that used the highest number of tool calls. Can you get it to use fewer?

Ideas to try:

* Change the system prompt to say "Combine operations where possible"
* Make the tool description say "You can use compound expressions like `(45 * 0.70) * 0.90`"
* Add an example expression in the `code` parameter description

### Discussion

Is fewer tool calls always better? What are the cost/latency tradeoffs of more granular decomposition? When would you want the model to show more work vs. be concise?

---

## Part 6: Agent loops

### Run it

1. Pick your framework and open the corresponding file:

    | Framework | File |
    | --------- | ---- |
    | PydanticAI | [examples/agent_trip_planner_pydanticai.py](examples/agent_trip_planner_pydanticai.py) |
    | LangChain | [examples/agent_trip_planner_langchain.py](examples/agent_trip_planner_langchain.py) |
    | Microsoft Agent Framework | [examples/agent_trip_planner_maf.py](examples/agent_trip_planner_maf.py) |

2. Run the file:

    ```bash
    uv run examples/agent_trip_planner_pydanticai.py
    # or
    uv run examples/agent_trip_planner_langchain.py
    # or
    uv run examples/agent_trip_planner_maf.py
    ```

3. The agent must search flights, search hotels, verify the budget, and suggest an activity with the remaining budget. Observe the **Turn** labels — which calls are parallel vs single, and how many turns the model takes.

4. Change model to one of the other models by un-commenting a `MODEL =` line at the top, and re-run the file.

### What to observe

* **Parallel vs serial**: gpt-5.5 batches `search_flights` + `search_hotels` in one parallel turn; other models may call them one at a time
* **Budget checks**: gpt-5.5/DeepSeek verify once; Kimi/Mistral explore multiple flight+hotel combos
* **Dependency awareness**: `search_activities` needs the remaining budget from `check_budget`. Does the model wait for the result, or guess the value and call them in parallel?

### Exercise: Control agent thoroughness

Can you get the "thorough" models to be more concise, or the "concise" models to explore more options?

Ideas to try:

* Add "Present only the single best option" to the system prompt
* Add "Always check at least 3 combinations before recommending" to the system prompt
* Change the budget to $400 (tighter constraint) — does behavior change?

---

## Part 7: Evaluations

Now quantify what you observed.

### 7a: Basic programmatic evals

```bash
uv run examples/evals_basic.py
```

This runs test cases (letter counting, spatial reasoning, tool calling) across all models and checks against ground truth. No LLM judge needed — just exact match and schema validation.

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

---

## Part 8: Prompt optimization

You've been manually tweaking prompts all workshop. [DSPy](https://dspy.ai/) automates that loop: you define a metric, and its GEPA optimizer generates prompt variations, evaluates them, and keeps the best.

### Run it

1. Open [examples/dspy_optimize.py](examples/dspy_optimize.py)
2. Run the file:

    ```bash
    uv run examples/dspy_optimize.py
    ```

    This takes ~6 minutes — GEPA evaluates dozens of prompt candidates against training examples. Watch the terminal as it runs.

3. Watch the terminal output as GEPA proposes prompts. It discovers strategies like explicit word-counting procedures, verify-then-rewrite loops, and final verification passes — the same techniques a prompt engineer would find manually, but discovered automatically.

4. After optimization, the script prints the winning instructions and saves the optimized program to `dspy_multi_constraint_optimized.json`.

### What to observe

* **Real improvement**: Mistral baseline scores 0% on the multi-constraint task (wrong word count). After optimization, it scores 100%. GEPA found instructions that teach the model to count words explicitly before outputting.
* **GEPA's generated prompts**: The optimizer discovers a structured procedure — draft each line, enumerate words to verify count, rewrite if wrong, do a final pass. This is exactly what a human prompt engineer would discover through trial and error.
* **Try a different student model**: Change `STUDENT_MODEL` to `Kimi-K2.6` and re-run. The optimizer will generate different instructions tuned to that model's quirks.

### Discussion

* How does automated prompt optimization compare to manual tweaking?
* When would you use DSPy in production vs. hand-tuning?
* What tasks benefit most from prompt optimization vs. needing a better model?

---

## Recap

| What we tested | Winner(s) | What helps weaker models |
| -------------- | --------- | ------------------------ |
| Raw reasoning (counting, spatial) | gpt-5.5, Kimi | Chain-of-thought prompts, code tools |
| Grounding / hallucination | gpt-5.5, Kimi, DeepSeek | Stronger system prompt instructions |
| Tool arg normalization | gpt-5.5, Kimi | Tighter parameter descriptions, examples |
| Tool loop efficiency | gpt-5.5, DeepSeek | Fewer calls = lower cost/latency |

**Key takeaway**: "Just swap the model" is never just swapping the model. Prompts, tool definitions, and output strategies all need tuning per model. Evals let you quantify instead of guessing.
