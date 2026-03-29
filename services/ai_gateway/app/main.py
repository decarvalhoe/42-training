from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .defense import compute_session_result, create_session, get_session, score_answer
from .intent import route_intent
from .librarian import search_librarian
from .llm_client import get_mentor_response
from .repository import load_curriculum, load_progression
from .reviewer import build_review
from .schemas import (
    DefenseAnswerRequest,
    DefenseAnswerResponse,
    DefenseQuestionOut,
    DefenseQuestionResult,
    DefenseResultResponse,
    DefenseStartRequest,
    DefenseStartResponse,
    IntentRequest,
    IntentResponse,
    LibrarianRequest,
    LibrarianResponse,
    MentorRequest,
    MentorResponse,
    ReviewerRequest,
    ReviewerResponse,
    SourceUsed,
)

logger = logging.getLogger(__name__)
REQUIRED_MENTOR_FIELDS = ("observation", "question", "hint", "next_action")

app = FastAPI(title="42-training AI Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai_gateway"}


@app.get("/api/v1/source-policy")
def source_policy() -> dict[str, object]:
    curriculum = load_curriculum()
    result: dict[str, object] = curriculum["source_policy"]
    return result


@app.post("/api/v1/intent", response_model=IntentResponse)
def intent_route(request: IntentRequest) -> IntentResponse:
    return IntentResponse(**route_intent(request))  # type: ignore[arg-type]


def _static_fallback(request: MentorRequest, focus: str, active_course: str) -> dict[str, str]:
    """Hardcoded mentor response used when the LLM is unavailable."""
    if request.track_id == "shell":
        hint = "Reduis le probleme a une commande, un fichier, puis verifie le resultat avec `ls`, `cat` ou `echo $?`."
        next_action = "Ecris la commande exacte que tu veux tester, execute-la, puis note ce qui change dans le systeme de fichiers."
    elif request.track_id == "c":
        hint = "Separe bien logique, compilation et memoire. Commence toujours avec `cc -Wall -Wextra -Werror`."
        next_action = "Isole un cas minimal reproductible, compile, puis explique en une phrase ce que ton programme devrait faire."
    else:
        hint = "Garde Python simple d'abord: une fonction courte, une entree, une sortie. Pour l'IA, justifie toujours la source et le critere d'evaluation."
        next_action = "Reformule ton objectif en script minimal ou en pipeline RAG minimal avant d'ajouter une couche d'automatisation."

    return {
        "observation": f"Tu travailles sur {focus}. Le cours actif du profil est {active_course} et ta demande touche: {request.question[:120]}",
        "question": f"Quel est le plus petit resultat observable que tu veux obtenir sur {focus}?",
        "hint": hint,
        "next_action": next_action,
    }


def _build_provenance(
    curriculum: dict,
    track: dict,
    module: dict | None,
    source: str,
) -> tuple[list[SourceUsed], Literal["high", "medium", "low"], str]:
    """Build provenance metadata for a mentor response.

    Returns (sources_used, confidence_level, reasoning_trace).

    Confidence is derived from the tiers of sources actually consulted:
    - high: response based on official_42 curriculum data
    - medium: community docs or testers supplemented the response
    - low: fallback with no retrieval, or only solution metadata
    """
    sources: list[SourceUsed] = []

    # The curriculum JSON is always consulted (track/module lookup)
    sources.append(SourceUsed(tier="official_42", label="42 Lausanne curriculum data"))

    # If a module was matched, record it
    if module:
        sources.append(
            SourceUsed(
                tier="official_42",
                label=f"Module: {module['title']} (track: {track['id']})",
            )
        )

    # Add recommended resources that match the track
    for resource in curriculum.get("recommended_resources", []):
        if resource.get("tier") in ("official_42", "community_docs", "testers_and_tooling"):
            sources.append(
                SourceUsed(
                    tier=resource["tier"],
                    label=resource["label"],
                    url=resource.get("url"),
                )
            )

    # Determine confidence from source tiers and response source
    tiers_present = {s.tier for s in sources}
    confidence: Literal["high", "medium", "low"]
    if source == "llm" and "official_42" in tiers_present:
        confidence = "high"
    elif (
        (source == "fallback" and "official_42" in tiers_present)
        or "community_docs" in tiers_present
        or "testers_and_tooling" in tiers_present
    ):
        confidence = "medium"
    else:
        confidence = "low"

    # Build reasoning trace
    if source == "llm":
        trace = (
            f"Response generated by LLM using curriculum data for track '{track['id']}'"
            + (f", module '{module['id']}'" if module else "")
            + ". Source policy applied: official_42 as ground truth, community_docs for explanation."
        )
    else:
        trace = (
            f"Static fallback response using hardcoded guidance for track '{track['id']}'"
            + (f", module '{module['id']}'" if module else "")
            + ". LLM was unavailable. Confidence reduced accordingly."
        )

    return sources, confidence, trace


def _curriculum_tier_ids(curriculum: dict) -> list[str]:
    return [tier["id"] for tier in curriculum["source_policy"]["tiers"]]


def _mentor_source_policy_ids(curriculum: dict) -> list[str]:
    return [tier_id for tier_id in _curriculum_tier_ids(curriculum) if tier_id != "blocked_solution_content"]


def _normalize_mentor_payload(payload: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for field in REQUIRED_MENTOR_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Mentor payload missing valid '{field}'")
        normalized[field] = value.strip()
    return normalized


@app.post("/api/v1/mentor/respond", response_model=MentorResponse)
def mentor_respond(request: MentorRequest) -> MentorResponse:
    curriculum = load_curriculum()
    progression = load_progression()
    track = next((item for item in curriculum["tracks"] if item["id"] == request.track_id), None)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    module = None
    if request.module_id:
        module = next((item for item in track.get("modules", []) if item["id"] == request.module_id), None)

    active_course = progression.get("learning_plan", {}).get("active_course", "shell")
    direct_solution_allowed = request.phase in {"advanced"}
    focus = module["title"] if module else track["title"]

    track_title = track["title"]
    module_title = module["title"] if module else None

    response_source = "llm"
    try:
        llm_result = _normalize_mentor_payload(get_mentor_response(request, track_title, module_title, active_course))
        observation = llm_result["observation"]
        question = llm_result["question"]
        hint = llm_result["hint"]
        next_action = llm_result["next_action"]
    except Exception:
        logger.warning("LLM call failed, using static fallback", exc_info=True)
        response_source = "fallback"
        fallback = _static_fallback(request, focus, active_course)
        observation = fallback["observation"]
        question = fallback["question"]
        hint = fallback["hint"]
        next_action = fallback["next_action"]

    sources_used, confidence_level, reasoning_trace = _build_provenance(
        curriculum,
        track,
        module,
        response_source,
    )

    return MentorResponse(
        status="ok",
        observation=observation,
        question=question,
        hint=hint,
        next_action=next_action,
        source_policy=_mentor_source_policy_ids(curriculum),
        direct_solution_allowed=direct_solution_allowed,
        sources_used=sources_used,
        confidence_level=confidence_level,
        reasoning_trace=reasoning_trace,
    )


@app.post("/api/v1/librarian/search", response_model=LibrarianResponse)
def librarian_search(request: LibrarianRequest) -> LibrarianResponse:
    return search_librarian(request)


@app.post("/api/v1/reviewer/review", response_model=ReviewerResponse)
def reviewer_review(request: ReviewerRequest) -> ReviewerResponse:
    curriculum = load_curriculum()
    track = next((t for t in curriculum["tracks"] if t["id"] == request.track_id), None)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    module = None
    if request.module_id:
        module = next(
            (m for m in track.get("modules", []) if m["id"] == request.module_id),
            None,
        )

    review = build_review(
        code=request.code,
        language=request.language,
        track=track,
        module=module,
        phase=request.phase,
    )

    return ReviewerResponse(
        status="ok",
        observation=review["observation"],
        questions=review["questions"],
        hint=review["hint"],
        next_action=review["next_action"],
        corrected_code=None,
    )


# --- Defense endpoints ---


@app.post("/api/v1/defense/start", response_model=DefenseStartResponse)
def defense_start(request: DefenseStartRequest) -> DefenseStartResponse:
    curriculum = load_curriculum()
    track = next((t for t in curriculum["tracks"] if t["id"] == request.track_id), None)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    module = next((m for m in track.get("modules", []) if m["id"] == request.module_id), None)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    session = create_session(track, module, request.phase, request.num_questions)

    return DefenseStartResponse(
        status="ok",
        session_id=session.session_id,
        track_id=session.track_id,
        module_id=session.module_id,
        questions=[
            DefenseQuestionOut(
                question_id=q.id,
                text=q.text,
                skill=q.skill,
            )
            for q in session.questions
        ],
        total_questions=len(session.questions),
    )


@app.post("/api/v1/defense/answer", response_model=DefenseAnswerResponse)
def defense_answer(request: DefenseAnswerRequest) -> DefenseAnswerResponse:
    session = get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.completed:
        raise HTTPException(status_code=400, detail="Session already completed")

    question = next((q for q in session.questions if q.id == request.question_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.answered:
        raise HTTPException(status_code=400, detail="Question already answered")

    score_val, feedback = score_answer(question, request.answer)
    question.score = score_val
    question.feedback = feedback
    question.answered = True

    remaining = sum(1 for q in session.questions if not q.answered)
    if remaining == 0:
        session.completed = True

    return DefenseAnswerResponse(
        status="ok",
        question_id=question.id,
        score=score_val,
        feedback=feedback,
        questions_remaining=remaining,
    )


@app.get("/api/v1/defense/{session_id}/result", response_model=DefenseResultResponse)
def defense_result(session_id: str) -> DefenseResultResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = compute_session_result(session)

    return DefenseResultResponse(
        status="ok",
        session_id=session.session_id,
        overall_score=result["overall_score"],
        passed=result["passed"],
        summary=result["summary"],
        question_results=[DefenseQuestionResult(**qr) for qr in result["question_results"]],
    )
