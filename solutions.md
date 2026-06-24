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

## Part 4: Structured outputs

### Expected results

Same date resolution, plus schema adherence — should return IATA airport codes (NRT, HND), not city names ("Tokyo") or city codes ("TYO").

| Model | origin_airport | destination_airport | departure | return | Schema adherence |
|-------|---------------|---------------------|-----------|--------|-----------------|
| **gpt-5.5** | SFO ✅ | "Tokyo" ❌ | 2026-07-04 ✅ | 2026-07-10 ✅ | City name instead of airport IATA code for destination |
| **Kimi-K2.6** | SFO ✅ | NRT ✅ | 2026-07-04 ✅ | 2026-07-10 ✅ | All fields correct |
| **Mistral-Large-3** | SFO ✅ | NRT ✅ | 2026-07-04 ✅ | 2026-07-10 ✅ | All fields correct |
| **DeepSeek-V4-Flash** | SFO or "San Francisco" | "Tokyo" or "TYO" | 2026-07-04 ✅ | 2026-07-10 ✅ | Dates correct but often returns city names instead of IATA airport codes |

GPT models use `responses.parse()` with strict `text_format` (enforced schema). Other models fall back to function calling with `tool_choice="required"` since they don't enforce structured output schemas.

---

## Part 5: Code execution

### Expected results

Same letter-counting task but with an `execute_python` tool. All models get 13 ✅, but efficiency varies.

| Model | Tool calls | Behavior |
|-------|-----------|----------|
| **gpt-5.5** | 1 | Clean single-shot solution |
| **Mistral-Large-3** | 1 | Clean single-shot solution |
| **Kimi-K2.6** | 2 | Verbose code with word-by-word breakdown, retries because `print()` returns `None` |
| **DeepSeek-V4-Flash** | 8 | Keeps retrying because `print()` returns `None` — can't figure out to return an expression |
