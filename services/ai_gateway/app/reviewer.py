"""Reviewer role — peer-style code critique with solution-leakage guardrails.

The Reviewer follows the pedagogical contract: it produces an observation,
questions, a hint, and a next action. It NEVER corrects code directly.
This mirrors the 42 peer-review philosophy: challenge, question, guide.

Guardrails (issue #133):
- In foundation/practice/core phases, any output that resembles a complete
  solution is scrubbed and replaced by a pedagogical redirect.
- In advanced phase, slightly more detailed feedback is allowed but
  corrected code is still never provided.

The system prompt below defines the reviewer persona. In the MVP phase
the review logic is rule-based. When an LLM backend is added later,
the system prompt will be sent as-is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# --- System prompt for future LLM integration ---
REVIEWER_SYSTEM_PROMPT = """\
You are a peer reviewer in a 42-style learning environment.

RULES — you MUST follow all of these:
1. NEVER provide corrected code, fixed code, or solution code.
2. NEVER rewrite the student's code.
3. Ask questions that lead the student to find the issue themselves.
4. Point out what you observe without telling them what to change.
5. Give one small hint — not the answer.
6. Suggest one concrete next action the student can take to verify or improve.

Your output must contain:
- observation: what you notice about the code (factual, no judgment)
- questions: 2-3 questions that guide the student toward the issue
- hint: one small directional hint
- next_action: one concrete step the student should try next

You must REFUSE to provide corrected code even if asked directly.
"""

# ---------------------------------------------------------------------------
# Guardrail detection — patterns that indicate solution leakage
# ---------------------------------------------------------------------------

#: Phrases that betray a direct solution being given away.
SOLUTION_GIVEAWAY_PATTERNS: list[str] = [
    "voici la solution",
    "voici le code",
    "copie ce code",
    "here is the solution",
    "here is the code",
    "copy this code",
    "the fix is",
    "the answer is",
    "you should write",
    "replace with",
    "change it to",
    "correct version",
    "corrected code",
    "fixed version",
    "la correction est",
    "remplace par",
]

#: Regex that detects multi-line code blocks (fenced or indented) which
#: are likely complete solutions rather than illustrative snippets.
_CODE_BLOCK_RE = re.compile(r"```[\s\S]{40,}```", re.MULTILINE)

#: Regex for lines that look like full function/program definitions in
#: C, shell, or Python — indicators of a complete solution.
_FULL_SOLUTION_PATTERNS: list[re.Pattern[str]] = [
    # C: full function body with braces
    re.compile(r"(int|void|char)\s+\w+\s*\([^)]*\)\s*\{", re.MULTILINE),
    # Shell: complete command pipeline (3+ stages)
    re.compile(r"(\|.*){2,}", re.MULTILINE),
    # Python: function def with return
    re.compile(r"def\s+\w+\(.*\).*:\s*\n.*return\s", re.MULTILINE),
]

#: Phases where guardrails are strict (no solutions allowed).
STRICT_PHASES: frozenset[str] = frozenset({"foundation", "practice", "core"})


@dataclass
class GuardrailResult:
    """Outcome of running guardrail checks on reviewer output."""

    clean: bool = True
    violations: list[str] = field(default_factory=list)
    scrubbed_fields: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_solution_leakage(text: str, phase: str) -> GuardrailResult:
    """Scan *text* for solution-leakage indicators.

    In strict phases (foundation/practice/core) both giveaway phrases and
    code blocks are flagged.  In advanced phase only explicit giveaway
    phrases are checked.
    """
    result = GuardrailResult()
    text_lower = text.lower()

    # 1. Check giveaway phrases (all phases)
    for pattern in SOLUTION_GIVEAWAY_PATTERNS:
        if pattern in text_lower:
            result.clean = False
            result.violations.append(f"giveaway_phrase:{pattern}")

    # 2. In strict phases, also flag code blocks and full solutions
    if phase in STRICT_PHASES:
        if _CODE_BLOCK_RE.search(text):
            result.clean = False
            result.violations.append("code_block_detected")

        for pat in _FULL_SOLUTION_PATTERNS:
            if pat.search(text):
                result.clean = False
                result.violations.append(f"full_solution_pattern:{pat.pattern[:40]}")
                break  # one is enough

    return result


def scrub_review_field(value: str, phase: str, field_name: str) -> tuple[str, bool]:
    """Return a safe version of *value*, scrubbing solution leakage.

    Returns (scrubbed_value, was_scrubbed).
    """
    result = check_solution_leakage(value, phase)
    if result.clean:
        return value, False

    # Replace the leaking content with a pedagogical redirect
    redirects: dict[str, str] = {
        "observation": (
            "The reviewer noticed something interesting in your code. "
            "Take a closer look at the logic flow and variable states."
        ),
        "hint": ("There is a detail worth investigating — try tracing your code step by step with a simple input."),
        "next_action": ("Re-read your code line by line, predict what each line does, then verify with a small test."),
    }
    return redirects.get(field_name, redirects["observation"]), True


def build_review(
    code: str,
    language: str,
    track: dict[str, Any],
    module: dict[str, Any] | None,
    phase: str,
) -> dict[str, Any]:
    """Build a peer-style review for the given code snippet.

    This is the MVP rule-based implementation. It inspects the code
    for common patterns per language and generates pedagogical feedback
    without ever providing corrections.

    All output fields are passed through guardrail checks before being
    returned. In strict phases, any detected solution leakage is scrubbed.
    """
    focus = module["title"] if module else track["title"]
    code_lines = code.strip().splitlines()
    line_count = len(code_lines)

    observation = _build_observation(code, language, focus, line_count)
    questions = _build_questions(code, language, module)
    hint = _build_hint(code, language)
    next_action = _build_next_action(language, phase)

    # --- Guardrail pass ---------------------------------------------------
    guardrail = GuardrailResult()

    observation, obs_scrubbed = scrub_review_field(observation, phase, "observation")
    hint, hint_scrubbed = scrub_review_field(hint, phase, "hint")
    next_action, na_scrubbed = scrub_review_field(next_action, phase, "next_action")

    if obs_scrubbed:
        guardrail.clean = False
        guardrail.scrubbed_fields.append("observation")
    if hint_scrubbed:
        guardrail.clean = False
        guardrail.scrubbed_fields.append("hint")
    if na_scrubbed:
        guardrail.clean = False
        guardrail.scrubbed_fields.append("next_action")

    # Scrub questions individually
    safe_questions: list[str] = []
    for q in questions:
        q_result = check_solution_leakage(q, phase)
        if q_result.clean:
            safe_questions.append(q)
        else:
            guardrail.clean = False
            guardrail.scrubbed_fields.append("questions")
            safe_questions.append("What behaviour do you expect from this part of your code?")
    questions = safe_questions

    return {
        "observation": observation,
        "questions": questions,
        "hint": hint,
        "next_action": next_action,
        "guardrail": guardrail,
    }


# ---------------------------------------------------------------------------
# Internal helpers (unchanged logic, now protected by guardrail post-pass)
# ---------------------------------------------------------------------------


def _build_observation(code: str, language: str, focus: str, line_count: int) -> str:
    """Factual observation about the submitted code."""
    parts = [f"Code submitted for review in context of {focus} ({line_count} lines, language: {language})."]

    if language == "c":
        if "malloc" in code and "free" not in code:
            parts.append("Memory allocation detected without a visible free.")
        if "#include" not in code and line_count > 3:
            parts.append("No includes visible in this snippet.")
    elif language == "shell":
        if "rm " in code and "-f" in code:
            parts.append("Destructive command with force flag detected.")
        if "$(" in code or "`" in code:
            parts.append("Command substitution detected.")
    elif language == "python":
        if "except:" in code or "except Exception:" in code:
            parts.append("Broad exception handling detected.")
        if "import *" in code:
            parts.append("Wildcard import detected.")

    return " ".join(parts)


def _build_questions(code: str, language: str, module: dict[str, Any] | None) -> list[str]:
    """Generate 2-3 peer-style questions — never corrections."""
    questions: list[str] = []

    # Universal questions
    questions.append("What is the expected output of this code for a simple test case?")

    if language == "c":
        if "malloc" in code:
            questions.append("What happens to the allocated memory when this function returns?")
        if "while" in code or "for" in code:
            questions.append("How do you know the loop will terminate?")
        if "*" in code:
            questions.append("Can you trace the pointer value at each step?")
    elif language == "shell":
        if "|" in code:
            questions.append("What does each stage of this pipeline produce?")
        if ">" in code or ">>" in code:
            questions.append("What happens if the target file already exists?")
        if "$" in code:
            questions.append("What value does each variable hold at this point?")
    elif language == "python":
        if "def " in code:
            questions.append("What does this function return for edge-case inputs?")
        if "for " in code or "while " in code:
            questions.append("What happens when the input is empty?")
        if "open(" in code:
            questions.append("What happens if the file does not exist?")

    if module and module.get("skills"):
        skill_sample = module["skills"][0]
        questions.append(f"How does this code relate to the skill '{skill_sample}' you are practicing?")

    # Keep 2-3 questions
    return questions[:3]


def _build_hint(code: str, language: str) -> str:
    """One small directional hint — never the answer."""
    if language == "c":
        if "malloc" in code and "free" not in code:
            return "Think about the lifecycle of every allocated block."
        if "printf" in code and "\\n" not in code and '"' in code:
            return "Check what happens to your output without a newline at the end."
        return "Try running with -Wall -Wextra -Werror and read each warning carefully."
    elif language == "shell":
        if "rm " in code:
            return "Before running destructive commands, try echoing the arguments first."
        if "|" in code:
            return "Test each segment of the pipeline in isolation before chaining."
        return "Run the command, then check the exit code with echo $?."
    else:
        if "except:" in code:
            return "Consider what specific exception types you actually expect here."
        if "import *" in code:
            return "Try importing only what you need and see if anything breaks."
        return "Add a print statement at the point where you are least sure of the value."


def _build_next_action(language: str, phase: str) -> str:
    """One concrete step the student should try next."""
    if phase == "foundation":
        if language == "c":
            return "Compile with warnings enabled, pick the first warning, and explain it in your own words."
        elif language == "shell":
            return "Run the command on a test file, then describe what changed using ls -la."
        else:
            return "Run the script with a minimal input and print every intermediate value."
    elif phase == "practice":
        if language == "c":
            return "Run your code through valgrind and investigate the first error it reports."
        elif language == "shell":
            return "Write a second version using a different approach and compare the outputs."
        else:
            return "Write a simple test case that covers the most likely failure and run it."
    else:
        return "Explain your approach to a peer in two sentences, then check if the code matches that explanation."
