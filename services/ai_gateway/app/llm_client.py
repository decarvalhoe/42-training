from __future__ import annotations

import json
import logging
import os

import anthropic

from .schemas import MentorRequest

logger = logging.getLogger(__name__)

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


def _build_user_message(request: MentorRequest, track_title: str, module_title: str | None, active_course: str) -> str:
    parts = [
        f"Track: {request.track_id} ({track_title})",
        f"Module: {module_title or 'aucun specifie'}",
        f"Phase: {request.phase}",
        f"Pace: {request.pace_mode}",
        f"Cours actif du profil: {active_course}",
        f"Question de l'apprenant: {request.question}",
    ]
    if request.phase == "advanced":
        parts.append("NOTE: Phase advanced — une solution complete est permise si l'apprenant montre sa comprehension.")
    else:
        parts.append(f"NOTE: Phase {request.phase} — PAS de solution complete. Guide uniquement.")
    return "\n".join(parts)


def get_mentor_response(
    request: MentorRequest,
    track_title: str,
    module_title: str | None,
    active_course: str,
) -> dict[str, str]:
    """Call Claude API and return structured mentor response.

    Raises on API errors or malformed JSON so the caller can fall back.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    user_message = _build_user_message(request, track_title, module_title, active_course)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    block = message.content[0]
    raw: str = block.text.strip()  # type: ignore[union-attr]
    result: dict[str, str] = json.loads(raw)
    return result
