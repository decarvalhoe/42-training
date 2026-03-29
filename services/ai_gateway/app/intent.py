from __future__ import annotations

import json
import os
from typing import Any

from .schemas import IntentRequest, IntentRole

ROLE_ROUTES: dict[IntentRole, str] = {
    "mentor": "/api/v1/mentor/respond",
    "librarian": "/api/v1/librarian/search",
    "reviewer": "/api/v1/reviewer/review",
    "examiner": "/api/v1/defense/start",
}

INTENT_CLASSIFIER_PROMPT = """\
Tu es un classifieur d'intention pour un AI gateway pedagogique.

Tu dois choisir exactement UN role actif parmi:
- mentor: aide pedagogique generale, blocage, indice, prochaine etape
- librarian: recherche de ressources, documentation, references, sources
- reviewer: demande de revue de code, critique, feedback sur un snippet
- examiner: simulation de defense orale, questions d'evaluation, quiz

Regles:
- Choisis reviewer si le message demande explicitement une review de code ou contient un snippet a commenter.
- Choisis librarian si la demande principale est de trouver des ressources ou de la documentation.
- Choisis examiner si l'utilisateur veut etre questionne, evalue, ou simuler une defense.
- Sinon, choisis mentor.

Reponds UNIQUEMENT en JSON valide avec cette structure exacte:
{
  "active_role": "mentor|librarian|reviewer|examiner",
  "reason": "phrase courte",
  "confidence": 0.0
}

Pas de markdown. Pas de texte avant ou apres le JSON.
"""

_REVIEWER_KEYWORDS = (
    "review",
    "reviewer",
    "relis",
    "relire",
    "feedback",
    "critique",
    "peer review",
    "mon code",
    "voici mon code",
    "snippet",
)
_LIBRARIAN_KEYWORDS = (
    "documentation",
    "doc ",
    "docs",
    "ressource",
    "resource",
    "source",
    "reference",
    "référence",
    "lien",
    "link",
    "article",
    "chercher",
    "find me",
    "where can i read",
    "where can i find",
    "man page",
    "norminette",
)
_EXAMINER_KEYWORDS = (
    "defense",
    "défense",
    "oral",
    "exam",
    "examiner",
    "quiz",
    "interroge",
    "question me",
    "test my understanding",
    "simulate evaluation",
    "mock interview",
    "evalue",
    "évalue",
)
_MENTOR_KEYWORDS = (
    "je bloque",
    "i'm stuck",
    "i am stuck",
    "stuck",
    "help",
    "aide",
    "indice",
    "hint",
    "next step",
    "prochaine etape",
    "prochaine étape",
    "comment commencer",
    "how do i start",
    "explain",
    "expliquer",
)
_CODE_MARKERS = (
    "```",
    "#include",
    "int main",
    "printf(",
    "malloc(",
    "free(",
    "def ",
    "import ",
    "try:",
    "except",
    "echo ",
    "grep ",
    "cat ",
    "while ",
    "for ",
)
_ROLE_PRIORITY: dict[IntentRole, int] = {
    "mentor": 1,
    "librarian": 2,
    "reviewer": 3,
    "examiner": 4,
}


def _build_anthropic_client(api_key: str) -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def _extract_text_content(message: Any) -> str:
    text_blocks: list[str] = []
    for block in getattr(message, "content", []):
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            text_blocks.append(text.strip())

    if not text_blocks:
        raise ValueError("Classifier response did not contain any text blocks")

    return "\n".join(text_blocks)


def _normalize_intent_payload(raw_text: str) -> dict[str, object]:
    payload_text = raw_text.strip()
    start = payload_text.find("{")
    end = payload_text.rfind("}")
    if start != -1 and end != -1 and start < end:
        payload_text = payload_text[start : end + 1]

    parsed = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise ValueError("Classifier response must be a JSON object")

    role = parsed.get("active_role")
    reason = parsed.get("reason")
    confidence = parsed.get("confidence", 0.9)

    if role not in ROLE_ROUTES:
        raise ValueError("Classifier response returned an invalid role")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Classifier response missing valid reason")
    if not isinstance(confidence, (int, float)):
        raise ValueError("Classifier response missing valid confidence")

    return {
        "active_role": role,
        "reason": reason.strip(),
        "confidence": max(0.0, min(float(confidence), 1.0)),
    }


def _build_classifier_message(request: IntentRequest) -> str:
    parts = [
        f"Message utilisateur: {request.message}",
        f"Track: {request.track_id or 'non specifie'}",
        f"Module: {request.module_id or 'non specifie'}",
        f"Phase: {request.phase}",
    ]
    parts.append("Retourne uniquement le role le plus approprie pour la prochaine action du systeme.")
    return "\n".join(parts)


def classify_intent_with_llm(request: IntentRequest) -> dict[str, object]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = _build_anthropic_client(api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=120,
        temperature=0,
        system=INTENT_CLASSIFIER_PROMPT,
        messages=[{"role": "user", "content": [{"type": "text", "text": _build_classifier_message(request)}]}],
    )

    raw = _extract_text_content(message)
    return _normalize_intent_payload(raw)


def classify_intent_fallback(request: IntentRequest) -> dict[str, object]:
    normalized = " ".join(request.message.lower().split())
    scores: dict[IntentRole, int] = {"mentor": 1, "librarian": 0, "reviewer": 0, "examiner": 0}
    matches: dict[IntentRole, list[str]] = {"mentor": [], "librarian": [], "reviewer": [], "examiner": []}

    if any(marker in normalized for marker in _CODE_MARKERS):
        scores["reviewer"] += 3
        matches["reviewer"].append("code markers")

    for keyword in _REVIEWER_KEYWORDS:
        if keyword in normalized:
            scores["reviewer"] += 2
            matches["reviewer"].append(keyword)

    for keyword in _LIBRARIAN_KEYWORDS:
        if keyword in normalized:
            scores["librarian"] += 2
            matches["librarian"].append(keyword)

    for keyword in _EXAMINER_KEYWORDS:
        if keyword in normalized:
            scores["examiner"] += 2
            matches["examiner"].append(keyword)

    for keyword in _MENTOR_KEYWORDS:
        if keyword in normalized:
            scores["mentor"] += 1
            matches["mentor"].append(keyword)

    best_role = max(scores, key=lambda role: (scores[role], _ROLE_PRIORITY[role]))  # type: ignore[arg-type]
    best_matches = matches[best_role]
    confidence = min(0.55 + 0.08 * scores[best_role], 0.95)

    if best_matches:
        reason = f"Fallback matched {best_role} cues: {', '.join(best_matches[:3])}."
    else:
        reason = "Fallback defaulted to mentor because no stronger routing signal was found."

    return {
        "active_role": best_role,
        "reason": reason,
        "confidence": round(confidence, 2),
    }


def route_intent(request: IntentRequest) -> dict[str, object]:
    try:
        result = classify_intent_with_llm(request)
        classifier = "llm"
    except Exception:
        result = classify_intent_fallback(request)
        classifier = "fallback"

    active_role = result["active_role"]
    return {
        "status": "ok",
        "active_role": active_role,
        "route": ROLE_ROUTES[active_role],  # type: ignore[index]
        "reason": result["reason"],
        "confidence": result["confidence"],
        "classifier": classifier,
    }
