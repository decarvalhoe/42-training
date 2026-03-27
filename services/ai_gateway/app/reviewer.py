"""Reviewer role — peer-style code critique.

The Reviewer follows the pedagogical contract: it produces an observation,
questions, a hint, and a next action. It NEVER corrects code directly.
This mirrors the 42 peer-review philosophy: challenge, question, guide.

The system prompt below defines the reviewer persona. In the MVP phase
the review logic is rule-based. When an LLM backend is added later,
the system prompt will be sent as-is.
"""

from __future__ import annotations

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
    """
    focus = module["title"] if module else track["title"]
    code_lines = code.strip().splitlines()
    line_count = len(code_lines)

    observation = _build_observation(code, language, focus, line_count)
    questions = _build_questions(code, language, module)
    hint = _build_hint(code, language)
    next_action = _build_next_action(language, phase)

    return {
        "observation": observation,
        "questions": questions,
        "hint": hint,
        "next_action": next_action,
    }


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


def _build_questions(code: str, language: str, module: dict | None) -> list[str]:
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
