from __future__ import annotations

import json
import logging
import os
from typing import Any

from .mentor_memory import MentorTurn
from .schemas import MentorRequest

logger = logging.getLogger(__name__)
REQUIRED_RESPONSE_FIELDS = ("observation", "question", "hint", "next_action")

SYSTEM_PROMPT = """\
Tu es un mentor pedagogique pour la preparation a 42 Lausanne.

## Contrat pedagogique strict

Tu ne fournis JAMAIS de solution complete. Tu guides l'apprenant avec exactement 4 elements:

1. **Observation** — Decris ce que l'apprenant semble faire ou bloquer.
2. **Question** — Pose UNE question utile qui pousse a reflechir.
3. **Indice** — Donne UN indice qui oriente sans reveler la reponse.
4. **Action suivante** — Propose UNE action concrete et minimale a tester.

## Politique de sources

- Sources officielles 42 = verite de reference
- Documentation communautaire = explication et cartographie
- Testers et outils = verification
- Repos de solutions = metadata uniquement, JAMAIS de code copie

## Regles absolues

- JAMAIS de solution complete en phase foundation, practice ou core.
- En phase advanced uniquement, tu PEUX montrer un exemple complet SI l'apprenant a demontre sa comprehension.
- Approche socratique: fais reflechir, ne donne pas la reponse.
- Adapte le niveau de detail au pace_mode (slow = plus de contexte, intensive = plus direct).
- Reponds TOUJOURS en francais.

## Format de reponse

Reponds UNIQUEMENT en JSON valide avec cette structure exacte:
{
  "observation": "...",
  "question": "...",
  "hint": "...",
  "next_action": "..."
}

Pas de texte avant ou apres le JSON. Pas de markdown autour du JSON.
"""


def _build_history_block(conversation_history: list[MentorTurn]) -> list[str]:
    if not conversation_history:
        return []

    lines = ["Historique recent de la session:"]
    for index, turn in enumerate(conversation_history, start=1):
        lines.extend(
            [
                f"Echange {index} - apprenant: {turn['user_question']}",
                f"Echange {index} - mentor observation: {turn['mentor_observation']}",
                f"Echange {index} - mentor question: {turn['mentor_question']}",
                f"Echange {index} - mentor hint: {turn['mentor_hint']}",
                f"Echange {index} - mentor next_action: {turn['mentor_next_action']}",
            ]
        )
    lines.append("Utilise cet historique pour eviter de repeter les memes indices et pour construire sur les essais deja faits.")
    return lines


def _build_user_message(
    request: MentorRequest,
    track_title: str,
    module_title: str | None,
    active_course: str,
    conversation_history: list[MentorTurn] | None = None,
) -> str:
    parts = [
        f"Learner: {request.learner_id}",
        f"Track: {request.track_id} ({track_title})",
        f"Module: {module_title or 'aucun specifie'}",
        f"Phase: {request.phase}",
        f"Pace: {request.pace_mode}",
        f"Cours actif du profil: {active_course}",
        f"Question de l'apprenant: {request.question}",
    ]
    parts.extend(_build_history_block(conversation_history or []))
    if request.phase == "advanced":
        parts.append(
            "NOTE: Phase advanced — une solution complete est permise UNIQUEMENT si "
            "l'apprenant montre deja sa comprehension."
        )
    else:
        parts.append(f"NOTE: Phase {request.phase} — PAS de solution complete. Guide uniquement.")
    parts.append("IMPORTANT: respecte strictement le contrat pedagogique et retourne uniquement du JSON valide.")
    return "\n".join(parts)


def _extract_text_content(message: Any) -> str:
    text_blocks: list[str] = []
    for block in getattr(message, "content", []):
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            text_blocks.append(text.strip())

    if not text_blocks:
        raise ValueError("Claude response did not contain any text blocks")

    return "\n".join(text_blocks)


def _parse_response_payload(raw_text: str) -> dict[str, str]:
    payload_text = raw_text.strip()
    start = payload_text.find("{")
    end = payload_text.rfind("}")
    if start != -1 and end != -1 and start < end:
        payload_text = payload_text[start : end + 1]

    parsed = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise ValueError("Claude response must be a JSON object")

    normalized: dict[str, str] = {}
    for field in REQUIRED_RESPONSE_FIELDS:
        value = parsed.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Claude response missing valid '{field}' field")
        normalized[field] = value.strip()
    return normalized


def _build_anthropic_client(api_key: str) -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def get_mentor_response(
    request: MentorRequest,
    track_title: str,
    module_title: str | None,
    active_course: str,
    conversation_history: list[MentorTurn] | None = None,
) -> dict[str, str]:
    """Call Claude API and return structured mentor response.

    Raises on API errors or malformed JSON so the caller can fall back.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = _build_anthropic_client(api_key)
    user_message = _build_user_message(
        request,
        track_title,
        module_title,
        active_course,
        conversation_history=conversation_history,
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
    )

    raw = _extract_text_content(message)
    return _parse_response_payload(raw)
