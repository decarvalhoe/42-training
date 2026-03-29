"use client";

import { useEffect, useMemo, useState } from "react";

import {
  createReviewAttempt,
  listReviewAttempts,
  type EvidenceArtifact,
  type ReviewAttemptRecord,
} from "@/services/reviewEvidence";

type ModuleOption = {
  id: string;
  title: string;
  phase: string;
  trackId: string;
  trackTitle: string;
};

type Props = {
  modules: ModuleOption[];
};

type FormState = {
  learnerId: string;
  reviewerId: string;
  moduleId: string;
  score: string;
  feedback: string;
  codeSnippet: string;
  evidenceNotes: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const REVIEW_LENSES = [
  "Correctness and edge cases",
  "Naming and readability",
  "Memory discipline",
  "Build or runtime failure points",
  "Defense readiness",
] as const;

const INITIAL_FORM: FormState = {
  learnerId: "default",
  reviewerId: "peer-reviewer",
  moduleId: "",
  score: "",
  feedback: "",
  codeSnippet: "",
  evidenceNotes: "",
};

function validateForm(values: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!values.reviewerId.trim()) {
    errors.reviewerId = "Reviewer ID is required.";
  }
  if (!values.moduleId) {
    errors.moduleId = "Select the reviewed module.";
  }
  if (values.codeSnippet.trim().length < 8) {
    errors.codeSnippet = "Add a meaningful code or command snippet.";
  }
  if (values.feedback.trim().length < 12) {
    errors.feedback = "Add review notes with a minimum level of detail.";
  }
  if (values.score && (Number.isNaN(Number(values.score)) || Number(values.score) < 0 || Number(values.score) > 100)) {
    errors.score = "Score must stay between 0 and 100.";
  }

  return errors;
}

function moduleLabel(moduleId: string, modules: ModuleOption[]) {
  const module = modules.find((item) => item.id === moduleId);
  return module ? `${module.trackTitle} — ${module.title}` : moduleId;
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function buildArtifacts(notes: string, selectedLenses: string[]): EvidenceArtifact[] {
  const lines = notes
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const noteArtifacts = lines.map((line, index) => ({
    kind: "review-note",
    label: `Review note ${index + 1}`,
    content: line,
  }));

  if (selectedLenses.length === 0) {
    return noteArtifacts;
  }

  return [
    ...noteArtifacts,
    {
      kind: "review-focus",
      label: "Guided review focus",
      content: selectedLenses.join(" | "),
    },
  ];
}

export default function ReviewClient({ modules }: Props) {
  const [form, setForm] = useState<FormState>({ ...INITIAL_FORM, moduleId: modules[0]?.id ?? "" });
  const [errors, setErrors] = useState<FormErrors>({});
  const [selectedLenses, setSelectedLenses] = useState<string[]>([REVIEW_LENSES[0], REVIEW_LENSES[4]]);
  const [items, setItems] = useState<ReviewAttemptRecord[]>([]);
  const [loadingState, setLoadingState] = useState<"loading" | "ready" | "error">("loading");
  const [sourceMode, setSourceMode] = useState<"live" | "mocked">("live");
  const [submitState, setSubmitState] = useState<"idle" | "submitting">("idle");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error">("success");

  useEffect(() => {
    let cancelled = false;

    async function loadItems() {
      try {
        const result = await listReviewAttempts();
        if (cancelled) {
          return;
        }
        setItems(result.items);
        setSourceMode(result.mocked ? "mocked" : "live");
        setLoadingState("ready");
      } catch {
        if (!cancelled) {
          setLoadingState("error");
        }
      }
    }

    void loadItems();

    return () => {
      cancelled = true;
    };
  }, []);

  const reviewQuestions = useMemo(
    () =>
      selectedLenses.map((lens) => {
        if (lens === "Correctness and edge cases") {
          return "Which edge cases still fail or remain untested?";
        }
        if (lens === "Naming and readability") {
          return "Which names or control-flow choices slow down understanding?";
        }
        if (lens === "Memory discipline") {
          return "Where could allocation, ownership or cleanup still break?";
        }
        if (lens === "Build or runtime failure points") {
          return "What would fail first at compile time or runtime and why?";
        }
        return "How would you defend these choices orally without showing the solution?";
      }),
    [selectedLenses]
  );

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setFeedback(null);
  }

  function toggleLens(value: string) {
    setSelectedLenses((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
    setFeedback(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validateForm(form);
    setErrors(nextErrors);
    setFeedback(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitState("submitting");
    try {
      const result = await createReviewAttempt({
        learnerId: form.learnerId.trim() || undefined,
        reviewerId: form.reviewerId.trim(),
        moduleId: form.moduleId,
        codeSnippet: form.codeSnippet.trim(),
        feedback: form.feedback.trim(),
        questions: reviewQuestions,
        score: form.score ? Number(form.score) : undefined,
        evidenceArtifacts: buildArtifacts(form.evidenceNotes, selectedLenses),
      });

      setItems((current) => [result.item, ...current]);
      setSourceMode(result.mocked ? "mocked" : "live");
      setFeedbackTone("success");
      setFeedback(`Review submitted for ${moduleLabel(form.moduleId, modules)}.`);
      setForm((current) => ({
        ...current,
        score: "",
        feedback: "",
        codeSnippet: "",
        evidenceNotes: "",
      }));
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(error instanceof Error ? error.message : "Unable to submit the review.");
    } finally {
      setSubmitState("idle");
    }
  }

  if (loadingState === "loading") {
    return (
      <section className="panel review-shell">
        <h2>Loading review workspace...</h2>
      </section>
    );
  }

  if (loadingState === "error") {
    return (
      <section className="panel review-shell">
        <h2>Review workspace unavailable</h2>
        <p className="muted">The page could not load recent review attempts.</p>
      </section>
    );
  }

  return (
    <section className="review-shell">
      <article className="panel review-form-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Submission</p>
            <h2>Submit a guided review</h2>
          </div>
          <span className="pill">{sourceMode === "live" ? "API live" : "Mocked fallback"}</span>
        </div>

        <form className="review-form" noValidate onSubmit={handleSubmit}>
          <div className="review-grid">
            <label className="defense-field">
              <span>Module</span>
              <select value={form.moduleId} onChange={(event) => updateField("moduleId", event.target.value)}>
                {modules.map((module) => (
                  <option key={module.id} value={module.id}>
                    {module.trackTitle} — {module.title}
                  </option>
                ))}
              </select>
              {errors.moduleId && <small className="login-error">{errors.moduleId}</small>}
            </label>

            <label className="defense-field">
              <span>Reviewer ID</span>
              <input value={form.reviewerId} onChange={(event) => updateField("reviewerId", event.target.value)} />
              {errors.reviewerId && <small className="login-error">{errors.reviewerId}</small>}
            </label>

            <label className="defense-field">
              <span>Learner ID</span>
              <input value={form.learnerId} onChange={(event) => updateField("learnerId", event.target.value)} />
            </label>

            <label className="defense-field">
              <span>Score (optional)</span>
              <input
                type="number"
                min="0"
                max="100"
                value={form.score}
                onChange={(event) => updateField("score", event.target.value)}
              />
              {errors.score && <small className="login-error">{errors.score}</small>}
            </label>
          </div>

          <div className="review-lens-list">
            {REVIEW_LENSES.map((lens) => (
              <label key={lens} className={`review-lens ${selectedLenses.includes(lens) ? "review-lens--active" : ""}`}>
                <input
                  type="checkbox"
                  checked={selectedLenses.includes(lens)}
                  onChange={() => toggleLens(lens)}
                />
                <span>{lens}</span>
              </label>
            ))}
          </div>

          <label className="defense-field">
            <span>Code or command snippet</span>
            <textarea
              className="defense-textarea"
              value={form.codeSnippet}
              onChange={(event) => updateField("codeSnippet", event.target.value)}
              placeholder="Paste the function, command sequence or excerpt you want reviewed."
            />
            {errors.codeSnippet && <small className="login-error">{errors.codeSnippet}</small>}
          </label>

          <label className="defense-field">
            <span>Review notes</span>
            <textarea
              className="defense-textarea"
              value={form.feedback}
              onChange={(event) => updateField("feedback", event.target.value)}
              placeholder="Describe what a peer should challenge, confirm or re-explain."
            />
            {errors.feedback && <small className="login-error">{errors.feedback}</small>}
          </label>

          <label className="defense-field">
            <span>Evidence notes</span>
            <textarea
              className="defense-textarea"
              value={form.evidenceNotes}
              onChange={(event) => updateField("evidenceNotes", event.target.value)}
              placeholder="One line per artifact: command output, self-note, checklist item, warning..."
            />
          </label>

          <div className="review-guidance panel">
            <p className="eyebrow">Generated reviewer prompts</p>
            <div className="stack-list">
              {reviewQuestions.map((question) => (
                <span key={question} className="pill">
                  {question}
                </span>
              ))}
            </div>
          </div>

          <button type="submit" className="action-btn" disabled={submitState === "submitting"}>
            {submitState === "submitting" ? "Submitting..." : "Submit review"}
          </button>
        </form>

        {feedback && (
          <div
            className={`login-feedback ${
              feedbackTone === "success" ? "login-feedback--success" : "login-feedback--error"
            }`}
          >
            {feedback}
          </div>
        )}
      </article>

      <aside className="panel review-history-panel">
        <p className="eyebrow">Recent attempts</p>
        <h2>Review history</h2>
        <div className="review-history-list">
          {items.map((item) => (
            <article key={item.id} className="review-history-card">
              <div className="card-topline">
                <span>{moduleLabel(item.moduleId, modules)}</span>
                <span>{formatTimestamp(item.createdAt)}</span>
              </div>
              <strong>{item.reviewerId}</strong>
              <p className="muted">{item.feedback}</p>
              <div className="review-history-meta">
                <span>{item.score !== null ? `${item.score}/100` : "No score"}</span>
                <span>{item.evidenceArtifacts.length} artifacts</span>
              </div>
            </article>
          ))}
        </div>
      </aside>
    </section>
  );
}
