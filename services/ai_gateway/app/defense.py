"""Oral defense MVP flow — question generation and scoring.

Simulates a 42-style oral defense where the learner must explain their
understanding. Questions are generated from module skills, objectives,
and exit criteria. The system never reveals answers — it scores based
on whether the learner demonstrates understanding.

Sessions are stored in-memory (MVP). A proper persistence layer will
replace this once the database is available.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DefenseQuestion:
    id: str
    text: str
    skill: str
    expected_keywords: list[str]
    answered: bool = False
    score: float = 0.0
    feedback: str = ""


@dataclass
class DefenseSession:
    session_id: str
    track_id: str
    module_id: str
    phase: str
    questions: list[DefenseQuestion] = field(default_factory=list)
    completed: bool = False


# In-memory session store (MVP)
_sessions: dict[str, DefenseSession] = {}


def get_session(session_id: str) -> DefenseSession | None:
    return _sessions.get(session_id)


def create_session(
    track: dict[str, Any],
    module: dict[str, Any],
    phase: str,
    num_questions: int = 3,
) -> DefenseSession:
    """Create a new defense session with generated questions."""
    session_id = uuid.uuid4().hex[:12]
    questions = _generate_questions(track, module, phase, num_questions)
    session = DefenseSession(
        session_id=session_id,
        track_id=track["id"],
        module_id=module["id"],
        phase=phase,
        questions=questions,
    )
    _sessions[session_id] = session
    return session


def score_answer(question: DefenseQuestion, answer: str) -> tuple[float, str]:
    """Score a learner's answer and produce pedagogical feedback.

    Scoring is rule-based (MVP). A future version will use LLM evaluation.
    The scorer never reveals the correct answer — it only assesses whether
    the learner demonstrated understanding.

    Returns (score, feedback) where score is 0.0 to 1.0.
    """
    answer_lower = answer.lower().strip()

    if len(answer_lower) < 10:
        return 0.0, "Your answer is too brief. Try explaining in your own words what this concept means and how you would use it."

    # Check for keyword presence (partial credit)
    matched = [kw for kw in question.expected_keywords if kw.lower() in answer_lower]
    keyword_ratio = len(matched) / max(len(question.expected_keywords), 1)

    # Check for explanation quality signals
    explains = any(
        marker in answer_lower
        for marker in ["because", "parce que", "car ", "donc ", "so ", "means ", "permet ", "sert a", "signifie"]
    )
    uses_example = any(
        marker in answer_lower
        for marker in ["for example", "par exemple", "e.g.", "like ", "comme ", "si on", "if we"]
    )

    # Composite score
    score = keyword_ratio * 0.5
    if explains:
        score += 0.3
    if uses_example:
        score += 0.2
    score = min(score, 1.0)

    # Generate feedback (pedagogical — never reveals answer)
    if score >= 0.7:
        feedback = f"Good understanding demonstrated. You covered key aspects of '{question.skill}'."
        if not uses_example:
            feedback += " Try adding a concrete example next time to strengthen your explanation."
    elif score >= 0.4:
        feedback = f"Partial understanding of '{question.skill}'. You touched on some important points but your explanation could go deeper."
        if not explains:
            feedback += " Try explaining *why* this concept matters, not just *what* it is."
    else:
        feedback = f"Your explanation of '{question.skill}' needs more depth. Think about what this concept does, why it exists, and how you would demonstrate it."

    return round(score, 2), feedback


def compute_session_result(session: DefenseSession) -> dict[str, Any]:
    """Compute final defense result for a completed session."""
    answered = [q for q in session.questions if q.answered]
    if not answered:
        return {
            "overall_score": 0.0,
            "passed": False,
            "summary": "No questions were answered.",
            "question_results": [],
        }

    total_score = sum(q.score for q in answered)
    overall = round(total_score / len(session.questions), 2)

    question_results = [
        {
            "question_id": q.id,
            "question": q.text,
            "skill": q.skill,
            "score": q.score,
            "feedback": q.feedback,
            "answered": q.answered,
        }
        for q in session.questions
    ]

    passed = overall >= 0.5 and all(q.answered for q in session.questions)

    if passed:
        summary = f"Defense passed with {overall:.0%}. You demonstrated sufficient understanding of the module skills."
    elif not all(q.answered for q in session.questions):
        unanswered = len(session.questions) - len(answered)
        summary = f"Defense incomplete: {unanswered} question(s) unanswered. Score so far: {overall:.0%}."
    else:
        summary = f"Defense not passed ({overall:.0%}). Review the feedback for each question and revisit the module materials."

    return {
        "overall_score": overall,
        "passed": passed,
        "summary": summary,
        "question_results": question_results,
    }


# --- Question generation ---

# Question templates per language/track — Socratic style, never solution-revealing
_QUESTION_TEMPLATES: dict[str, list[str]] = {
    "shell": [
        "Explain in your own words what the command '{skill}' does and when you would use it.",
        "What would happen if you ran '{skill}' in the wrong directory? How would you recover?",
        "How would you verify that '{skill}' did what you expected?",
    ],
    "c": [
        "Explain the concept of '{skill}' in C and why it matters for writing correct programs.",
        "What could go wrong if '{skill}' is used incorrectly? How would you detect the problem?",
        "Describe a minimal scenario where '{skill}' is essential and explain your reasoning.",
    ],
    "python_ai": [
        "Explain '{skill}' in Python and describe a situation where you would use it.",
        "What would happen if you misused '{skill}'? How would you debug the issue?",
        "How does '{skill}' relate to writing clean, maintainable code?",
    ],
}

_OBJECTIVE_TEMPLATE = "In your own words, explain how you would: {objective}"
_EXIT_CRITERIA_TEMPLATE = "Demonstrate your understanding: {criterion}"


def _generate_questions(
    track: dict[str, Any],
    module: dict[str, Any],
    phase: str,
    num_questions: int,
) -> list[DefenseQuestion]:
    """Generate defense questions from module data.

    Sources questions from: skills, objectives, exit_criteria.
    Never generates questions that reveal solutions.
    """
    questions: list[DefenseQuestion] = []
    track_id = track["id"]
    templates = _QUESTION_TEMPLATES.get(track_id, _QUESTION_TEMPLATES["shell"])

    # Questions from skills
    skills = module.get("skills", [])
    for i, skill in enumerate(skills):
        if len(questions) >= num_questions:
            break
        template = templates[i % len(templates)]
        questions.append(
            DefenseQuestion(
                id=f"q-{uuid.uuid4().hex[:8]}",
                text=template.format(skill=skill),
                skill=skill,
                expected_keywords=_keywords_for_skill(skill, track_id),
            )
        )

    # Questions from objectives (if we need more)
    for objective in module.get("objectives", []):
        if len(questions) >= num_questions:
            break
        questions.append(
            DefenseQuestion(
                id=f"q-{uuid.uuid4().hex[:8]}",
                text=_OBJECTIVE_TEMPLATE.format(objective=objective.lower()),
                skill=objective.split()[0].lower(),
                expected_keywords=objective.lower().split()[:4],
            )
        )

    # Questions from exit criteria (if still need more)
    for criterion in module.get("exit_criteria", []):
        if len(questions) >= num_questions:
            break
        questions.append(
            DefenseQuestion(
                id=f"q-{uuid.uuid4().hex[:8]}",
                text=_EXIT_CRITERIA_TEMPLATE.format(criterion=criterion.lower()),
                skill="exit_criteria",
                expected_keywords=criterion.lower().split()[:4],
            )
        )

    return questions[:num_questions]


def _keywords_for_skill(skill: str, track_id: str) -> list[str]:
    """Return expected keywords for a given skill.

    These are used for scoring — the learner should mention these
    concepts when explaining the skill.
    """
    base = [skill.lower()]

    skill_keywords: dict[str, list[str]] = {
        # Shell
        "pwd": ["directory", "current", "path"],
        "ls": ["list", "files", "directory"],
        "cd": ["change", "directory", "path"],
        "mkdir": ["create", "directory"],
        "touch": ["create", "file", "timestamp"],
        "cp": ["copy", "file", "destination"],
        "mv": ["move", "rename", "file"],
        "rm": ["remove", "delete", "file"],
        "chmod": ["permission", "read", "write", "execute"],
        "pipe": ["output", "input", "chain"],
        "grep": ["search", "pattern", "text"],
        "redirect": ["output", "file", "write"],
        # C
        "malloc": ["memory", "allocate", "heap", "free"],
        "free": ["memory", "deallocate", "leak"],
        "pointers": ["address", "memory", "dereference"],
        "arrays": ["index", "element", "contiguous"],
        "variables": ["type", "value", "declare"],
        "functions": ["return", "parameter", "call"],
        "loops": ["iteration", "condition", "repeat"],
        # Python
        "classes": ["object", "method", "attribute"],
        "collections": ["list", "dict", "set"],
    }

    return base + skill_keywords.get(skill.lower(), [])


def clear_sessions() -> None:
    """Clear all sessions. Used for testing only."""
    _sessions.clear()
