# Solutions and experimental results

This file contains solutions and test results for the workshop exercises.
Peek here if you're stuck, but try the exercises yourself first!

Results are representative — non-deterministic models may vary between runs.

---

## Part 1: Single LLM calls

### Expected results

| Example | gpt-5.5 | Kimi-K2.6 | Mistral-Large-3 | DeepSeek-V4-Flash |
|---------|---------|-----------|-----------------|-------------------|
| **Letter counting** — count "e" in a sentence (correct: 13) | 13 ✅ | 13 ✅ | 8–10 ❌ | 6 ❌ |
| **Spatial reasoning** — multi-step rotation (correct: Southeast) | Southeast ✅ | Southeast ✅ | Northeast ❌ | West ❌ |
| **Self-calibration** — confidence rating (lower = more honest) | 65 | 55 | 85 | 85 |
| **Multi-constraint** — acrostic + word count + format | ✅ all constraints | ✅ all constraints | ❌ fails word count | ✅ all constraints |

### Exercise: Prompt strategies for letter counting

The baseline prompt gets 8 (Mistral) and 7 (DeepSeek) instead of the correct answer 13.

#### Prompt variants tested

| Prompt strategy | Mistral-Large-3 | DeepSeek-V4-Flash |
|---|---|---|
| **baseline** ("count carefully, give just the number") | 8 ❌ | 7 ❌ |
| **list_each** ("list every occurrence with its position, then count") | 7 ❌ | 13 ✅ |
| **word_by_word** ("break into words, count per word, then sum") | 13 ✅ | 13 ✅ |
| **step_by_step** ("think step by step, show your work") | 15 ❌ | 13 ✅ |
| **double_check** ("count twice, reconcile if they disagree") | 17 ❌ | 14 ❌ |

**Winner: "word by word"** — the only strategy that fixes both models.

#### Temperature experiments

Temperature varies the answer but never reaches 13 for either model:

| Temperature | Mistral-Large-3 | DeepSeek-V4-Flash |
|---|---|---|
| 0 | 8 | 7 |
| 0.3 | 8 | 8 |
| 0.7 | 10 | 8 |
| 1.0 | 10 | 6 |
| 1.5 | ERROR (exceeds max) | 7 |
| 2.0 | ERROR | 8 |

**Conclusion**: Temperature adds noise but can't fix a capability gap. Structured decomposition in the prompt is what works.

#### The winning prompt

```
How many times does the letter "e" appear in the following sentence?
"The elderly gentleman eagerly entered the elevator."

Break the sentence into individual words. For each word, count the number
of times "e" appears. Then sum all the per-word counts.
Give the final total as a number on the last line.
```

---

## Part 2: RAG

### Expected results

The question asks about honey bees AND carpenter bees, but the sources only contain carpenter bee info — honey bee nest construction is NOT in the sources.

| Model | Grounding behavior |
|-------|-------------------|
| **gpt-5.5** | ✅ Correctly states honey bee nest-building is "not described in the provided material" |
| **Kimi-K2.6** | ✅ Correctly states "sources do not include further details on how honey bees construct their hives" |
| **DeepSeek-V4-Flash** | ✅ Correctly states "key differences… are not available" from sources |
| **Mistral-Large-3** | ❌ Hallucinates honey bee details (wax combs, hexagonal cells, secreted beeswax) not present in sources |
| **claude-sonnet-4-5** | ✅ Correctly states "documents do not contain information about how honey bees construct their nests" |

### Exercise: Fixing Mistral's hallucination

The baseline system message is not strong enough to prevent Mistral from hallucinating honey bee facts. We tested 5 strategies:

| Strategy | Mistral stays grounded? | Key change |
|----------|------------------------|------------|
| **baseline** | ❌ No (wax, hexagonal, wax comb) | Original prompt |
| **explicit_refusal** ("if not in sources, say so clearly") | ❌ No (wax, wax comb) | Added refusal instruction |
| **never_make_up** ("NEVER make up information") | ❌ No (wax, wax comb) | Stronger prohibition |
| **structured_format** ("cite source ID or write [NOT IN SOURCES]") | ✅ Yes | Forced per-claim citation |
| **negative_example** ("Do NOT mention facts about honey bees unless...") | ✅ Yes | Topic-specific prohibition |

**Conclusion**: Gentle instructions ("say so clearly", "NEVER make up") are not enough for Mistral. What works:
1. **Structured format** — forcing the model to cite a source for every claim makes it realize it has no source for honey bee facts
2. **Negative example** — explicitly calling out the specific topic that shouldn't be hallucinated

#### Winning system messages

**Structured format approach:**
```
You are a helpful assistant that answers questions about insects.
You must use the data set to answer the questions.
For each claim you make, cite the source ID in square brackets.
If a part of the question cannot be answered from the provided sources, write: "[NOT IN SOURCES]" for that part.
Do not provide any information that does not appear in the sources.
The sources are in the format: <id>: <text>.
```

**Negative example approach:**
```
You are a helpful assistant that answers questions about insects.
You must use the data set to answer the questions,
you should not provide any info that is not in the provided sources.
Do NOT mention facts about honey bees unless they explicitly appear in the sources.
If the sources only cover one type of bee, only answer about that type and state that info about the other type is not available.
Cite the sources you used to answer the question inside square brackets.
The sources are in the format: <id>: <text>.
```

---

## Part 3: Tool calling

### Expected results

The model must parse a casual meeting request into structured tool arguments. The user says "me, Sarah from eng, Marcus, and that new PM Priya" — the schema says "List of attendee names only." The user says "It's virtual, on Microsoft Teams" — the schema says `'Virtual' for online meetings`.

| Model | attendees | location | title | timezone | duration |
|-------|-----------|----------|-------|----------|----------|
| **gpt-5.5** | `["Sarah","Marcus","Priya"]` ✅ | `"Virtual"` ✅ | Platform Team Sync | America/Los_Angeles ✅ | 30 ✅ |
| **Kimi-K2.6** | `["Sarah","Marcus","Priya"]` ✅ | `"Virtual"` ✅ | Platform Team Sync | America/Los_Angeles ✅ | 30 ✅ |
| **DeepSeek-V4-Flash** | `["me","Sarah","Marcus","Priya"]` ❌ | `"Virtual"` ✅ | Platform Team Sync | America/Los_Angeles ✅ | 30 ✅ |
| **Mistral-Large-3** | `["You","Sarah","Marcus","Priya"]` ❌ | `"Virtual (Microsoft Teams)"` ❌ | Platform Team Sync | America/Los_Angeles ✅ | 30 ✅ |

Key differences:
- **gpt-5.5, Kimi**: Correctly infer "me" is the organizer (not an attendee) and follow the schema's location format exactly
- **DeepSeek**: Passes "me" literally as an attendee name — doesn't interpret the schema instruction
- **Mistral**: Re-interprets "me" as "You" (!) and appends "(Microsoft Teams)" to location despite the schema specifying just `'Virtual'`

### Exercise: Improve tool argument quality

Tightening the attendees description to `"List of attendee names only (first name or full name). Do not include the organizer."` fixes DeepSeek. Adding `"Do not include the platform name"` to the location description fixes Mistral. With both changes, all models produce identical correct output.

---

## Part 4: Tool calling in a loop

### Expected results

Multi-step math word problem with a `calculate` tool. All models get $92.28 ✅, but decomposition granularity varies.

| Model | Tool calls | Decomposition strategy |
|-------|-----------|------------------------|
| **gpt-5.5** | 4 | Combines discount steps: `45 * (1 - 0.30)`, then loyalty, then multiply, then tax |
| **DeepSeek-V4-Flash** | 4 | Same as gpt-5.5: `45 * 0.70`, `31.50 * 0.90`, `28.35 * 3`, `85.05 * 1.085` |
| **Kimi-K2.6** | 4–5 | Sometimes includes a redundant tax-amount step before the final total |
| **Mistral-Large-3** | 7 | Decomposes every sub-operation: `45 * 0.30`, `45 - 13.5`, `31.5 * 0.10`, `31.5 - 3.15`, `3 * 28.35`, `85.05 * 0.085`, `85.05 + 7.23` |

**Key insight**: Mistral breaks every operation into its smallest components (compute discount amount, then subtract it) rather than combining them (`price * 0.70`). This costs more in API calls and latency but produces the same correct answer.

### Exercise: Reduce tool calls

Results may vary across runs, but adding guidance about compound expressions generally helps. For example, changing the system prompt to:

```
You are a helpful assistant. Use the calculate tool for computations.
Combine operations where possible — e.g. use '45 * 0.70' instead of
separate '45 * 0.30' and '45 - 13.5' calls.
```

Or adding to the tool's `expression` description:

```
"A single arithmetic expression, e.g. '(45 * 0.70) * 0.90'. Combine steps where possible to minimize calls."
```

---

## Part 5: Agent loops (trip planner)

### Expected results

Trip planning agent with budget constraint ($600 for flight + 3 nights hotel, SF→NYC) plus activity suggestion with remaining budget. The middleware logs tool calls grouped by turn, showing parallel vs serial patterns.

| Model | Turns | Pattern |
|-------|-------|---------|
| **gpt-5.5** | 3 | Turn 1 (parallel): search_flights + search_hotels → Turn 2: check_budget → Turn 3: search_activities(max_price=35) |
| **DeepSeek-V4-Flash** | 3 | Same as gpt-5.5 — correct dependency ordering, waits for remaining budget |
| **Mistral-Large-3** | 2–4 | Turn 1 (parallel): searches → Turn 2 (parallel): multiple check_budget calls → sometimes Turn 3: search_activities, sometimes skips it |
| **Kimi-K2.6** | 3–4 | Turn 1 (parallel): searches → Turn 2: check_budget → Turn 3: search_activities → sometimes Turn 4: extra check_budget |

**Key insights**:

1. **Parallel vs serial**: gpt-5.5/DeepSeek consistently batch independent calls (search_flights + search_hotels) in one parallel turn. Kimi/Mistral sometimes go fully sequential via MAF/LangChain.
2. **Dependency awareness**: `search_activities` needs the remaining budget from `check_budget`. GPT-5.5/DeepSeek correctly wait for the result. Kimi occasionally batches them in parallel (guessing max_price=35 before knowing it).
3. **Thoroughness**: Mistral/Kimi explore multiple budget combinations; GPT-5.5/DeepSeek verify only the best option.
4. **Instruction following**: Mistral sometimes forgets to call search_activities entirely, getting lost in budget exploration.

### Exercise solution

- **"Present only the single best option"** with Mistral: Reduces check_budget calls from 3→2 and fixes the issue of forgetting to call search_activities. Doesn't fully eliminate exploration but makes it more focused.
- **"Always check at least 3 flight+hotel combinations"** with gpt-5.5: Increases check_budget calls from 1→4 (all in parallel). The model now explores the full space before recommending.
- **Tightening budget to $400**: No combo fits (cheapest is Delta + Pod = $480), so all models must explore multiple options then acknowledge failure. GPT-5.5 goes from 1→2 budget checks; Mistral checks 3 combos. With $500, models can still find the Delta + Pod combo but must reject the direct-flight option first.
