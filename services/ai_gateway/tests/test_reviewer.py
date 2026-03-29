"""Tests for the Reviewer endpoint — peer-style code critique.

Key invariant: the Reviewer NEVER provides corrected code.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.reviewer import REVIEWER_SYSTEM_PROMPT, build_review

client = TestClient(app)

ENDPOINT = "/api/v1/reviewer/review"

# --- Sample code snippets for testing ---

C_CODE_MALLOC = """\
#include <stdlib.h>

char *ft_strdup(char *s)
{
    char *dup;
    int i;

    dup = malloc(strlen(s) + 1);
    i = 0;
    while (s[i])
    {
        dup[i] = s[i];
        i++;
    }
    dup[i] = '\\0';
    return (dup);
}
"""

SHELL_CODE_PIPE = """\
cat /etc/passwd | grep root | cut -d: -f1 > result.txt
"""

PYTHON_CODE_BROAD_EXCEPT = """\
def read_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None
"""


# === Endpoint tests ===


def test_reviewer_basic_c_review() -> None:
    response = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["observation"]
    assert len(data["questions"]) >= 2
    assert data["hint"]
    assert data["next_action"]


def test_reviewer_basic_shell_review() -> None:
    response = client.post(
        ENDPOINT,
        json={"code": SHELL_CODE_PIPE, "track_id": "shell", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["questions"]) >= 2


def test_reviewer_basic_python_review() -> None:
    response = client.post(
        ENDPOINT,
        json={
            "code": PYTHON_CODE_BROAD_EXCEPT,
            "track_id": "python_ai",
            "language": "python",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_reviewer_never_returns_corrected_code() -> None:
    """The corrected_code field must ALWAYS be null."""
    for payload in [
        {"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
        {"code": SHELL_CODE_PIPE, "track_id": "shell", "language": "shell"},
        {"code": PYTHON_CODE_BROAD_EXCEPT, "track_id": "python_ai", "language": "python"},
    ]:
        response = client.post(ENDPOINT, json=payload)
        data = response.json()
        assert data["corrected_code"] is None, f"corrected_code must be null, got: {data['corrected_code']}"


def test_reviewer_observation_is_factual_not_corrective() -> None:
    """Observation should describe what is seen, not fix anything."""
    response = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
    )
    data = response.json()
    obs = data["observation"].lower()
    # Should not contain corrective language
    assert "should be" not in obs
    assert "fix" not in obs
    assert "change to" not in obs
    assert "replace" not in obs


def test_reviewer_questions_are_questions() -> None:
    """Every question must end with a question mark."""
    response = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
    )
    data = response.json()
    for q in data["questions"]:
        assert q.endswith("?"), f"Question must end with '?': {q}"


def test_reviewer_with_module_context() -> None:
    response = client.post(
        ENDPOINT,
        json={
            "code": C_CODE_MALLOC,
            "track_id": "c",
            "module_id": "c-memory",
            "language": "c",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["questions"]) >= 2


def test_reviewer_detects_malloc_without_free() -> None:
    """C code with malloc but no free should trigger a memory observation."""
    response = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c"},
    )
    data = response.json()
    obs_lower = data["observation"].lower()
    assert "memory" in obs_lower or "alloc" in obs_lower


def test_reviewer_detects_broad_except() -> None:
    """Python code with bare except should trigger a hint about it."""
    response = client.post(
        ENDPOINT,
        json={
            "code": PYTHON_CODE_BROAD_EXCEPT,
            "track_id": "python_ai",
            "language": "python",
        },
    )
    data = response.json()
    assert "except" in data["hint"].lower() or "exception" in data["hint"].lower()


def test_reviewer_shell_pipe_questions() -> None:
    """Shell code with pipes should get pipeline-related questions."""
    response = client.post(
        ENDPOINT,
        json={"code": SHELL_CODE_PIPE, "track_id": "shell", "language": "shell"},
    )
    data = response.json()
    all_questions = " ".join(data["questions"]).lower()
    assert "pipeline" in all_questions or "stage" in all_questions or "file" in all_questions


def test_reviewer_invalid_track_returns_404() -> None:
    response = client.post(
        ENDPOINT,
        json={"code": "echo hello", "track_id": "nonexistent", "language": "shell"},
    )
    assert response.status_code == 404


def test_reviewer_empty_code_rejected() -> None:
    response = client.post(
        ENDPOINT,
        json={"code": "", "track_id": "shell", "language": "shell"},
    )
    assert response.status_code == 422


def test_reviewer_phase_affects_next_action() -> None:
    """Different phases should produce different next_action guidance."""
    resp_foundation = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c", "phase": "foundation"},
    )
    resp_practice = client.post(
        ENDPOINT,
        json={"code": C_CODE_MALLOC, "track_id": "c", "language": "c", "phase": "practice"},
    )
    assert resp_foundation.json()["next_action"] != resp_practice.json()["next_action"]


# === Unit tests for review logic ===


def test_build_review_returns_all_fields() -> None:
    track = {"id": "c", "title": "C / Core 42", "modules": []}
    result = build_review(
        code="int main() { return 0; }",
        language="c",
        track=track,
        module=None,
        phase="foundation",
    )
    assert "observation" in result
    assert "questions" in result
    assert "hint" in result
    assert "next_action" in result


def test_system_prompt_forbids_corrections() -> None:
    """The system prompt must explicitly forbid corrected code."""
    prompt_lower = REVIEWER_SYSTEM_PROMPT.lower()
    assert "never provide corrected code" in prompt_lower
    assert "never rewrite" in prompt_lower
