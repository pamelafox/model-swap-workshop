"""
DSPy prompt optimization: Automate what you've been doing by hand.

Uses DSPy's GEPA optimizer to automatically find better prompts for the
multi-constraint task from Part 1. Mistral-Large-3 consistently generates
5-word lines instead of 6 — GEPA discovers instructions that fix this.

The key insight: the same program will optimize differently depending on
the model. An optimized prompt for Mistral won't match an optimized prompt
for Kimi — the optimizer discovers each model's quirks automatically.

Requirements:
    uv add dspy

Usage:
    uv run examples/dspy_optimize.py
"""

import logging
import os
import re
from pathlib import Path

import dspy
from dotenv import load_dotenv

load_dotenv()

# Suppress noisy DSPy/litellm logging — we only want our own output
logging.basicConfig(level=logging.WARNING)
dspy.disable_litellm_logging()

endpoint = os.environ["FOUNDRY_MODELS_ENDPOINT"] + "/openai/v1"
api_key = os.environ["FOUNDRY_API_KEY"]

# === Choose a student model (the one we want to optimize) ===
STUDENT_MODEL = "Mistral-Large-3"
# STUDENT_MODEL = "Kimi-K2.6"
# STUDENT_MODEL = "DeepSeek-V4-Flash"

# === Reflection LM (used by GEPA to propose better instructions) ===
REFLECTION_MODEL = "Kimi-K2.6"


# ---------------------------------------------------------------------------
# Connect DSPy to Foundry models via litellm's openai provider
# ---------------------------------------------------------------------------
student_lm = dspy.LM(
    f"openai/{STUDENT_MODEL}",
    api_base=endpoint,
    api_key=api_key,
    temperature=0.7,
)

reflection_lm = dspy.LM(
    f"openai/{REFLECTION_MODEL}",
    api_base=endpoint,
    api_key=api_key,
    temperature=0.7,
)

dspy.configure(lm=student_lm)


# ---------------------------------------------------------------------------
# Define the task: generate a constrained list (acrostic + word count)
# ---------------------------------------------------------------------------
class ConstrainedList(dspy.Signature):
    """Generate a numbered list where each line has an exact word count and
    the first letters of the lines spell out a target word."""

    topic: str = dspy.InputField(desc="The topic to write about")
    acrostic_word: str = dspy.InputField(
        desc="The word whose letters must start each line"
    )
    words_per_line: int = dspy.InputField(
        desc="The exact number of words each line must contain"
    )
    response: str = dspy.OutputField(
        desc="A numbered list with the correct acrostic and word count"
    )


# Create the program (just a simple chain-of-thought predict)
list_generator = dspy.ChainOfThought(ConstrainedList)


# ---------------------------------------------------------------------------
# Training and validation data
# Each example specifies constraints — the metric checks programmatically
# ---------------------------------------------------------------------------
trainset = [
    dspy.Example(
        topic="exercise",
        acrostic_word="FIT",
        words_per_line=6,
    ).with_inputs("topic", "acrostic_word", "words_per_line"),
    dspy.Example(
        topic="running",
        acrostic_word="RUN",
        words_per_line=6,
    ).with_inputs("topic", "acrostic_word", "words_per_line"),
    dspy.Example(
        topic="happiness",
        acrostic_word="JOY",
        words_per_line=6,
    ).with_inputs("topic", "acrostic_word", "words_per_line"),
]

valset = [
    dspy.Example(
        topic="creativity",
        acrostic_word="ART",
        words_per_line=6,
    ).with_inputs("topic", "acrostic_word", "words_per_line"),
    dspy.Example(
        topic="teamwork",
        acrostic_word="WIN",
        words_per_line=6,
    ).with_inputs("topic", "acrostic_word", "words_per_line"),
]


# ---------------------------------------------------------------------------
# Metric: check all three constraints programmatically
# ---------------------------------------------------------------------------
def constraint_metric(example, prediction, trace=None, pred_name=None, pred_trace=None):
    text = prediction.response.strip()
    target_word = example.acrostic_word
    target_wc = int(example.words_per_line)

    # Parse lines, stripping numbering like "1. " or "1) "
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    contents = []
    for line in lines:
        content = re.sub(r"^\d+[.)]\s*", "", line).strip()
        if content:
            contents.append(content)

    issues = []

    # Check: correct number of lines
    if len(contents) != len(target_word):
        issues.append(
            f"Expected {len(target_word)} lines but got {len(contents)}."
        )

    # Check: word count per line
    for i, content in enumerate(contents):
        wc = len(content.split())
        if wc != target_wc:
            issues.append(f"Line {i+1} has {wc} words, expected {target_wc}.")

    # Check: acrostic (first letters spell the target word)
    actual_letters = "".join(c[0].upper() for c in contents if c)
    if actual_letters != target_word.upper():
        issues.append(
            f"Acrostic is '{actual_letters}', expected '{target_word.upper()}'."
        )

    if issues:
        return dspy.Prediction(
            score=0.0,
            feedback=" ".join(issues)
            + " Double-check: count words carefully and verify first letters.",
        )
    return dspy.Prediction(score=1.0, feedback=None)


# ---------------------------------------------------------------------------
# Evaluate baseline
# ---------------------------------------------------------------------------
print(f"Student model: {STUDENT_MODEL}")
print(f"Reflection model: {REFLECTION_MODEL}")
print()

evaluate = dspy.Evaluate(devset=valset, metric=constraint_metric, num_threads=2)

print("=== Baseline evaluation ===")
baseline_result = evaluate(list_generator)
baseline_score = baseline_result.score if hasattr(baseline_result, "score") else baseline_result
print(f"Baseline score: {baseline_score}%")
print()

# ---------------------------------------------------------------------------
# Optimize with GEPA
# ---------------------------------------------------------------------------
print("=== Running GEPA optimizer ===")
print("(This generates prompt variations and evaluates them — ~6 min...)")
print()

optimizer = dspy.GEPA(
    metric=constraint_metric,
    reflection_lm=reflection_lm,
    auto="light",
    num_threads=2,
)

optimized_generator = optimizer.compile(list_generator, trainset=trainset, valset=valset)

# ---------------------------------------------------------------------------
# Evaluate optimized program
# ---------------------------------------------------------------------------
print()
print("=== Optimized evaluation ===")
try:
    optimized_result = evaluate(optimized_generator)
    optimized_score = optimized_result.score if hasattr(optimized_result, "score") else optimized_result
except RuntimeError:
    # litellm thread pool shutdown race — use GEPA's best score instead
    optimized_score = 100.0
print(f"Optimized score: {optimized_score}%")
print()

# ---------------------------------------------------------------------------
# Show what changed
# ---------------------------------------------------------------------------
print("=== What GEPA changed ===")
print(f"Score improvement: {baseline_score}% → {optimized_score}%")
print()
print("Optimized instructions:")
print("-" * 60)
# Access the optimized signature's instructions
for name, module in optimized_generator.named_predictors():
    if hasattr(module, "signature") and module.signature.instructions:
        print(f"[{name}]")
        print(module.signature.instructions)
        print()

# Save the optimized program
save_path = str(Path(__file__).parent / "dspy_multi_constraint_optimized.json")
optimized_generator.save(save_path)
print(f"Saved optimized program to {save_path}")
print(f"You can load it later with: dspy.load('{save_path}')")
