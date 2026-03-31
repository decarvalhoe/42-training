"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createReviewAttempt,
  listReviewAttempts,
  type EvidenceArtifact,
  type ReviewAttemptRecord,
} from "@/services/reviewEvidence";
import {
  GuidedActionButton,
  GuidedBadge,
  GuidedEmptyState,
  GuidedField,
  GuidedPanel,
  GuidedSelect,
  GuidedSidebarSection,
  GuidedTextarea,
} from "@/app/components/GuidedSurface";

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
  if (
    values.score &&
    (Number.isNaN(Number(values.score)) ||
      Number(values.score) < 0 ||
      Number(values.score) > 100)
  ) {
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

function buildArtifacts(
  notes: string,
  selectedLenses: string[],
): EvidenceArtifact[] {
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
  const [form, setForm] = useState<FormState>({
    ...INITIAL_FORM,
    moduleId: modules[0]?.id ?? "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [selectedLenses, setSelectedLenses] = useState<string[]>([
    REVIEW_LENSES[0],
    REVIEW_LENSES[4],
  ]);
  const [items, setItems] = useState<ReviewAttemptRecord[]>([]);
  const [loadingState, setLoadingState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [sourceMode, setSourceMode] = useState<"live" | "mocked">("live");
  const [submitState, setSubmitState] = useState<"idle" | "submitting">("idle");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error">(
    "success",
  );

  const loadItems = useCallback(async (cancelledRef?: { current: boolean }) => {
    setLoadingState("loading");

    try {
      const result = await listReviewAttempts();
      if (cancelledRef?.current) {
        return;
      }
      setItems(result.items);
      setSourceMode(result.mocked ? "mocked" : "live");
      setLoadingState("ready");
    } catch {
      if (!cancelledRef?.current) {
        setLoadingState("error");
      }
    }
  }, []);

  useEffect(() => {
    const cancelledRef = { current: false };
    void loadItems(cancelledRef);

    return () => {
      cancelledRef.current = true;
    };
  }, [loadItems]);

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
    [selectedLenses],
  );

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setFeedback(null);
  }

  function toggleLens(value: string) {
    setSelectedLenses((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
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
      setFeedback(
        `Review submitted for ${moduleLabel(form.moduleId, modules)}.`,
      );
      setForm((current) => ({
        ...current,
        score: "",
        feedback: "",
        codeSnippet: "",
        evidenceNotes: "",
      }));
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(
        error instanceof Error ? error.message : "Unable to submit the review.",
      );
    } finally {
      setSubmitState("idle");
    }
  }

  if (loadingState === "loading") {
    return (
      <GuidedEmptyState
        title="Loading review workspace..."
        body="The guided review workspace is bootstrapping recent attempts and evidence prompts."
      />
    );
  }

  if (loadingState === "error") {
    return (
      <GuidedEmptyState
        title="Review workspace unavailable"
        body="The page could not load recent review attempts. Retry once the review endpoints are reachable again."
        action={
          <GuidedActionButton onClick={() => void loadItems()}>
            Retry
          </GuidedActionButton>
        }
      />
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_340px]">
      <div className="grid gap-4">
        <GuidedPanel className="px-6 py-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
                guided review // peer preparation
              </p>
              <h1 className="mt-4 font-mono text-3xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                Submit a guided review
              </h1>
              <p className="mt-4 text-sm leading-7 text-[var(--shell-muted)]">
                Prepare a peer-style evaluation before the real defense pressure
                hits. Frame the review lenses, attach evidence and leave a trace
                of the exact questions another learner should challenge.
              </p>
            </div>
            <GuidedBadge tone={sourceMode === "live" ? "success" : "warning"}>
              {sourceMode === "live" ? "API live" : "demo mode"}
            </GuidedBadge>
          </div>
        </GuidedPanel>

        <GuidedPanel className="px-6 py-6">
          <form
            className="review-form grid gap-6"
            noValidate
            onSubmit={handleSubmit}
          >
            <div className="grid gap-4 lg:grid-cols-2">
              <GuidedField label="Module">
                <GuidedSelect
                  value={form.moduleId}
                  onChange={(event) =>
                    updateField("moduleId", event.target.value)
                  }
                >
                  {modules.map((module) => (
                    <option key={module.id} value={module.id}>
                      {module.trackTitle} — {module.title}
                    </option>
                  ))}
                </GuidedSelect>
                {errors.moduleId ? (
                  <small className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]">
                    {errors.moduleId}
                  </small>
                ) : null}
              </GuidedField>

              <GuidedField label="Reviewer ID">
                <input
                  className="min-h-11 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-2 font-mono text-sm text-[var(--shell-ink)] outline-none transition-colors focus:border-[var(--shell-success)]"
                  value={form.reviewerId}
                  onChange={(event) =>
                    updateField("reviewerId", event.target.value)
                  }
                />
                {errors.reviewerId ? (
                  <small className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]">
                    {errors.reviewerId}
                  </small>
                ) : null}
              </GuidedField>

              <GuidedField label="Learner ID">
                <input
                  className="min-h-11 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-2 font-mono text-sm text-[var(--shell-ink)] outline-none transition-colors focus:border-[var(--shell-success)]"
                  value={form.learnerId}
                  onChange={(event) =>
                    updateField("learnerId", event.target.value)
                  }
                />
              </GuidedField>

              <GuidedField label="Score (optional)">
                <input
                  className="min-h-11 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-2 font-mono text-sm text-[var(--shell-ink)] outline-none transition-colors focus:border-[var(--shell-success)]"
                  type="number"
                  min="0"
                  max="100"
                  value={form.score}
                  onChange={(event) => updateField("score", event.target.value)}
                />
                {errors.score ? (
                  <small className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]">
                    {errors.score}
                  </small>
                ) : null}
              </GuidedField>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {REVIEW_LENSES.map((lens) => {
                const active = selectedLenses.includes(lens);
                return (
                  <label
                    key={lens}
                    className={`flex cursor-pointer items-start gap-3 border px-4 py-3 transition-colors ${
                      active
                        ? "border-[var(--shell-success)] bg-[var(--shell-success)]/8"
                        : "border-[var(--shell-border)] bg-[var(--shell-canvas)]"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleLens(lens)}
                      className="mt-1"
                    />
                    <span className="text-sm leading-6 text-[var(--shell-ink)]">
                      {lens}
                    </span>
                  </label>
                );
              })}
            </div>

            <GuidedField label="Code or command snippet">
              <GuidedTextarea
                value={form.codeSnippet}
                onChange={(event) =>
                  updateField("codeSnippet", event.target.value)
                }
                placeholder="Paste the function, command sequence or excerpt you want reviewed."
              />
              {errors.codeSnippet ? (
                <small className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]">
                  {errors.codeSnippet}
                </small>
              ) : null}
            </GuidedField>

            <GuidedField label="Review notes">
              <GuidedTextarea
                value={form.feedback}
                onChange={(event) =>
                  updateField("feedback", event.target.value)
                }
                placeholder="Describe what a peer should challenge, confirm or re-explain."
              />
              {errors.feedback ? (
                <small className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]">
                  {errors.feedback}
                </small>
              ) : null}
            </GuidedField>

            <GuidedField label="Evidence notes">
              <GuidedTextarea
                value={form.evidenceNotes}
                onChange={(event) =>
                  updateField("evidenceNotes", event.target.value)
                }
                placeholder="One line per artifact: command output, self-note, checklist item, warning..."
              />
            </GuidedField>

            <div className="flex flex-wrap gap-3">
              <GuidedActionButton
                type="submit"
                disabled={submitState === "submitting"}
              >
                {submitState === "submitting"
                  ? "Submitting..."
                  : "Submit review"}
              </GuidedActionButton>
            </div>

            {feedback ? (
              <div
                className={`border px-4 py-3 font-mono text-[10px] uppercase tracking-[0.24em] ${
                  feedbackTone === "success"
                    ? "border-[var(--shell-success)]/35 text-[var(--shell-success)]"
                    : "border-[var(--shell-danger)]/35 text-[var(--shell-danger)]"
                }`}
              >
                {feedback}
              </div>
            ) : null}
          </form>
        </GuidedPanel>
      </div>

      <div className="grid gap-4">
        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Generated reviewer prompts">
            <div className="flex flex-wrap gap-2">
              {reviewQuestions.map((question) => (
                <GuidedBadge key={question}>{question}</GuidedBadge>
              ))}
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Review lenses">
            <div className="space-y-2 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--shell-muted)]">
              {selectedLenses.map((lens) => (
                <p key={lens}>{lens}</p>
              ))}
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Recent attempts">
            <div className="space-y-3">
              {items.length === 0 ? (
                <p className="text-sm leading-6 text-[var(--shell-muted)]">
                  No review has been captured yet. The first submission will
                  appear here.
                </p>
              ) : (
                items.map((item) => (
                  <article
                    key={item.id}
                    className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4"
                  >
                    <div className="flex items-start justify-between gap-4 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
                      <span>{formatTimestamp(item.createdAt)}</span>
                      <span>
                        {item.score !== null ? `${item.score}/100` : "no score"}
                      </span>
                    </div>
                    <p className="mt-3 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                      {item.reviewerId}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-[var(--shell-muted)]">
                      {moduleLabel(item.moduleId, modules)}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">
                      {item.feedback}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <GuidedBadge>
                        {item.evidenceArtifacts.length} artifacts
                      </GuidedBadge>
                    </div>
                  </article>
                ))
              )}
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>
      </div>
    </div>
  );
}
