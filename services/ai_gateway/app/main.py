from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repository import load_curriculum, load_progression
from .schemas import MentorRequest, MentorResponse

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
    return curriculum["source_policy"]


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
    skills = ", ".join((module or track)["skills"][:3]) if module else track["title"]

    if request.track_id == "shell":
        hint = "Reduis le probleme a une commande, un fichier, puis verifie le resultat avec `ls`, `cat` ou `echo $?`."
        next_action = "Ecris la commande exacte que tu veux tester, execute-la, puis note ce qui change dans le systeme de fichiers."
    elif request.track_id == "c":
        hint = "Separe bien logique, compilation et memoire. Commence toujours avec `cc -Wall -Wextra -Werror`."
        next_action = "Isole un cas minimal reproductible, compile, puis explique en une phrase ce que ton programme devrait faire."
    else:
        hint = "Garde Python simple d'abord: une fonction courte, une entree, une sortie. Pour l'IA, justifie toujours la source et le critere d'evaluation."
        next_action = "Reformule ton objectif en script minimal ou en pipeline RAG minimal avant d'ajouter une couche d'automatisation."

    return MentorResponse(
        status="ok",
        observation=f"Tu travailles sur {focus}. Le cours actif du profil est {active_course} et ta demande touche: {request.question[:120]}",
        question=f"Quel est le plus petit resultat observable que tu veux obtenir sur {focus}?",
        hint=hint,
        next_action=next_action,
        source_policy=[
            "official_42",
            "community_docs",
            "testers_and_tooling",
            "solution_metadata_only",
        ],
        direct_solution_allowed=direct_solution_allowed,
    )
