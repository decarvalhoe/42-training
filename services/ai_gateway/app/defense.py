"""Oral defense MVP flow — question generation and scoring.

Simulates a 42-style oral defense where the learner must explain their
understanding. Questions are generated from module skills, objectives,
and exit criteria. The system never reveals answers — it scores based
on whether the learner demonstrates understanding.

Sessions are stored in-memory (MVP). A proper persistence layer will
replace this once the database is available.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .llm_client import get_defense_evaluation

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class DefenseQuestion:
    id: str
    text: str
    skill: str
    expected_keywords: list[str]
    answer: str = ""
    answered: bool = False
    score: float = 0.0
    feedback: str = ""
    timed_out: bool = False
    elapsed_seconds: float = 0.0


@dataclass
class DefenseSession:
    session_id: str
    track_id: str
    module_id: str
    phase: str
    learner_id: str | None = None
    reviewer_id: str | None = None
    questions: list[DefenseQuestion] = field(default_factory=list)
    question_time_limit_seconds: int = 60
    started_at: datetime = field(default_factory=_utc_now)
    current_question_started_at: datetime = field(default_factory=_utc_now)
    completed: bool = False
    review_attempt_persisted: bool = False


# In-memory session store (MVP)
_sessions: dict[str, DefenseSession] = {}


def get_session(session_id: str) -> DefenseSession | None:
    return _sessions.get(session_id)


def create_session(
    track: dict[str, Any],
    module: dict[str, Any],
    phase: str,
    learner_id: str | None = None,
    reviewer_id: str | None = None,
    num_questions: int = 3,
    question_time_limit_seconds: int = 60,
) -> DefenseSession:
    """Create a new defense session with generated questions."""
    now = _utc_now()
    session_id = uuid.uuid4().hex[:12]
    questions = _generate_questions(track, module, phase, num_questions)
    session = DefenseSession(
        session_id=session_id,
        track_id=track["id"],
        module_id=module["id"],
        phase=phase,
        learner_id=learner_id,
        reviewer_id=reviewer_id,
        questions=questions,
        question_time_limit_seconds=question_time_limit_seconds,
        started_at=now,
        current_question_started_at=now,
    )
    _sessions[session_id] = session
    return session


def _score_answer_rule_based(question: DefenseQuestion, answer: str) -> tuple[float, str]:
    """Fallback defense scorer used when LLM evaluation is unavailable."""
    answer_lower = answer.lower().strip()

    if len(answer_lower) < 10:
        return (
            0.0,
            "Your answer is too brief. Try explaining in your own words what this concept means and how you would use it.",
        )

    # Check for keyword presence (partial credit)
    matched = [kw for kw in question.expected_keywords if kw.lower() in answer_lower]
    keyword_ratio = len(matched) / max(len(question.expected_keywords), 1)

    # Check for explanation quality signals
    explains = any(
        marker in answer_lower
        for marker in ["because", "parce que", "car ", "donc ", "so ", "means ", "permet ", "sert a", "signifie"]
    )
    uses_example = any(
        marker in answer_lower for marker in ["for example", "par exemple", "e.g.", "like ", "comme ", "si on", "if we"]
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


def score_answer(
    question: DefenseQuestion,
    answer: str,
    *,
    track_id: str = "shell",
    module_id: str = "unknown-module",
    phase: str = "foundation",
) -> tuple[float, str]:
    """Score a learner's answer with Claude, then fall back to rules."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _score_answer_rule_based(question, answer)

    try:
        evaluation = get_defense_evaluation(
            track_id=track_id,
            module_id=module_id,
            phase=phase,
            question_text=question.text,
            skill=question.skill,
            expected_keywords=question.expected_keywords,
            answer=answer,
        )
        return float(evaluation["score"]), str(evaluation["feedback"])
    except Exception:
        logger.warning("Defense LLM scoring failed, using rule-based fallback", exc_info=True)
        return _score_answer_rule_based(question, answer)


def compute_session_result(session: DefenseSession) -> dict[str, Any]:
    """Compute final defense result for a completed session."""
    answered = [q for q in session.questions if q.answered]
    timed_out_questions = sum(1 for q in session.questions if q.timed_out)
    if not answered:
        return {
            "overall_score": 0.0,
            "passed": False,
            "summary": "No questions were answered.",
            "timed_out_questions": timed_out_questions,
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
            "timed_out": q.timed_out,
            "elapsed_seconds": q.elapsed_seconds,
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

    if timed_out_questions:
        summary += f" {timed_out_questions} question(s) exceeded the timer."

    return {
        "overall_score": overall,
        "passed": passed,
        "summary": summary,
        "timed_out_questions": timed_out_questions,
        "question_results": question_results,
    }


def get_current_question(session: DefenseSession) -> DefenseQuestion | None:
    for question in session.questions:
        if not question.answered:
            return question
    return None


def get_current_question_deadline(session: DefenseSession) -> datetime | None:
    if get_current_question(session) is None:
        return None
    return session.current_question_started_at + timedelta(seconds=session.question_time_limit_seconds)


def submit_answer(session: DefenseSession, question_id: str, answer: str) -> dict[str, Any]:
    if session.completed:
        raise ValueError("Session already completed")

    current_question = get_current_question(session)
    if current_question is None:
        session.completed = True
        raise ValueError("Session already completed")

    if question_id != current_question.id:
        raise ValueError("Questions must be answered in order")

    now = _utc_now()
    elapsed_seconds = round((now - session.current_question_started_at).total_seconds(), 2)
    deadline = get_current_question_deadline(session)
    timed_out = deadline is not None and now > deadline

    if timed_out:
        current_question.answer = answer
        score_val = 0.0
        feedback = (
            f"Time limit reached for '{current_question.skill}'. Try explaining the concept again from memory in one "
            "clear paragraph."
        )
    else:
        current_question.answer = answer
        score_val, feedback = score_answer(
            current_question,
            answer,
            track_id=session.track_id,
            module_id=session.module_id,
            phase=session.phase,
        )

    current_question.score = score_val
    current_question.feedback = feedback
    current_question.answered = True
    current_question.timed_out = timed_out
    current_question.elapsed_seconds = elapsed_seconds

    remaining = sum(1 for question in session.questions if not question.answered)
    next_question = get_current_question(session)
    next_question_deadline = None
    if next_question is None:
        session.completed = True
    else:
        session.current_question_started_at = now
        next_question_deadline = get_current_question_deadline(session)

    return {
        "question_id": current_question.id,
        "score": score_val,
        "feedback": feedback,
        "questions_remaining": remaining,
        "timed_out": timed_out,
        "elapsed_seconds": elapsed_seconds,
        "next_question_id": next_question.id if next_question else None,
        "next_question_deadline": next_question_deadline,
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
