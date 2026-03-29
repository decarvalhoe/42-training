"use client";

import { useState, useEffect, useCallback } from "react";

import { TerminalPane } from "@/app/components/TerminalPane";

/* ------------------------------------------------------------------ */
/*  Types matching the AI Gateway defense API                          */
/* ------------------------------------------------------------------ */

type DefenseQuestion = {
  question_id: string;
  text: string;
  skill: string;
  time_limit_seconds: number;
};

type DefenseStartResponse = {
  status: string;
  session_id: string;
  track_id: string;
  module_id: string;
  questions: DefenseQuestion[];
  total_questions: number;
  question_time_limit_seconds: number;
  active_question_id: string | null;
  started_at: string;
  current_question_deadline: string | null;
};

type DefenseAnswerResponse = {
  status: string;
  question_id: string;
  score: number;
  feedback: string;
  questions_remaining: number;
  timed_out: boolean;
  elapsed_seconds: number;
  next_question_id: string | null;
  next_question_deadline: string | null;
};

type QuestionResult = {
  question_id: string;
  question: string;
  skill: string;
  score: number;
  feedback: string;
  answered: boolean;
  timed_out: boolean;
  elapsed_seconds: number;
};

type DefenseResultResponse = {
  status: string;
  session_id: string;
  overall_score: number;
  passed: boolean;
  summary: string;
  timed_out_questions: number;
  question_results: QuestionResult[];
};

type Phase = "setup" | "active" | "results";

/* ------------------------------------------------------------------ */
/*  Module / track data passed from the server component               */
/* ------------------------------------------------------------------ */

type ModuleOption = {
  id: string;
  title: string;
  phase: string;
  trackId: string;
  trackTitle: string;
};

type TmuxSessionOption = {
  name: string;
  status: string;
  attached: boolean;
};

type Props = {
  modules: ModuleOption[];
  apiUrl: string;
  tmuxSessions?: TmuxSessionOption[];
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function DefenseClient({ modules, apiUrl, tmuxSessions = [] }: Props) {
  /* Setup state */
  const [selectedModule, setSelectedModule] = useState(modules[0]?.id ?? "");
  const [numQuestions, setNumQuestions] = useState(3);
  const [timeLimit, setTimeLimit] = useState(60);
  const [selectedTmux, setSelectedTmux] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* Session state */
  const [phase, setPhase] = useState<Phase>("setup");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<DefenseQuestion[]>([]);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [deadline, setDeadline] = useState<Date | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);

  /* Answer state */
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lastFeedback, setLastFeedback] = useState<{
    score: number;
    feedback: string;
    timed_out: boolean;
  } | null>(null);

  /* Results state */
  const [results, setResults] = useState<DefenseResultResponse | null>(null);

  /* Derived */
  const currentModule = modules.find((m) => m.id === selectedModule);
  const currentQuestion = questions[activeQuestionIndex] ?? null;

  /* ---------------------------------------------------------------- */
  /*  Timer                                                            */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    if (phase !== "active" || !deadline) return;

    const tick = () => {
      const remaining = Math.max(
        0,
        Math.ceil((deadline.getTime() - Date.now()) / 1000)
      );
      setSecondsLeft(remaining);
    };

    tick();
    const interval = setInterval(tick, 500);
    return () => clearInterval(interval);
  }, [phase, deadline]);

  /* ---------------------------------------------------------------- */
  /*  Start defense                                                    */
  /* ---------------------------------------------------------------- */

  async function handleStart() {
    if (!selectedModule) return;
    setLoading(true);
    setError(null);

    const trackId = currentModule?.trackId ?? "shell";
    const modulePhase = currentModule?.phase ?? "foundation";

    try {
      /* Capture terminal context if a tmux session is selected */
      let terminalContext: Record<string, unknown> | undefined;
      if (selectedTmux) {
        try {
          const paneRes = await fetch(
            `${apiUrl}/api/v1/tmux/pane/${encodeURIComponent(selectedTmux)}`
          );
          if (paneRes.ok) {
            const pane = await paneRes.json();
            terminalContext = {
              panes: { [selectedTmux]: pane.content },
            };
          }
        } catch {
          /* Terminal context is optional — proceed without it */
        }
      }

      const res = await fetch(`${apiUrl}/api/v1/defense/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          track_id: trackId,
          module_id: selectedModule,
          phase: modulePhase,
          num_questions: numQuestions,
          question_time_limit_seconds: timeLimit,
          ...(terminalContext && { terminal_context: terminalContext }),
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `API error ${res.status}`);
      }

      const data: DefenseStartResponse = await res.json();

      setSessionId(data.session_id);
      setQuestions(data.questions);
      setActiveQuestionIndex(0);
      setAnswer("");
      setLastFeedback(null);
      setResults(null);

      if (data.current_question_deadline) {
        setDeadline(new Date(data.current_question_deadline));
      }

      setPhase("active");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start defense");
    } finally {
      setLoading(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Submit answer                                                    */
  /* ---------------------------------------------------------------- */

  async function handleSubmitAnswer() {
    if (!sessionId || !currentQuestion || submitting) return;
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/defense/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestion.question_id,
          answer,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `API error ${res.status}`);
      }

      const data: DefenseAnswerResponse = await res.json();

      setLastFeedback({
        score: data.score,
        feedback: data.feedback,
        timed_out: data.timed_out,
      });

      if (data.questions_remaining === 0) {
        /* Fetch final results */
        await fetchResults();
      } else {
        /* Move to next question after a brief pause to show feedback */
        setTimeout(() => {
          setActiveQuestionIndex((i) => i + 1);
          setAnswer("");
          setLastFeedback(null);
          if (data.next_question_deadline) {
            setDeadline(new Date(data.next_question_deadline));
          }
        }, 2500);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit answer"
      );
    } finally {
      setSubmitting(false);
    }
  }

  /* ---------------------------------------------------------------- */
  /*  Fetch results                                                    */
  /* ---------------------------------------------------------------- */

  const fetchResults = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/defense/${sessionId}/result`
      );
      if (!res.ok) {
        throw new Error(`Failed to fetch results: ${res.status}`);
      }
      const data: DefenseResultResponse = await res.json();
      setResults(data);
      setPhase("results");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch results"
      );
    }
  }, [sessionId, apiUrl]);

  /* ---------------------------------------------------------------- */
  /*  Reset                                                            */
  /* ---------------------------------------------------------------- */

  function handleReset() {
    setPhase("setup");
    setSessionId(null);
    setQuestions([]);
    setActiveQuestionIndex(0);
    setAnswer("");
    setLastFeedback(null);
    setResults(null);
    setError(null);
    setDeadline(null);
  }

  /* ---------------------------------------------------------------- */
  /*  Render: Setup                                                    */
  /* ---------------------------------------------------------------- */

  if (phase === "setup") {
    return (
      <section className="defense-setup panel">
        <p className="eyebrow">Configuration</p>
        <h2>Start a defense session</h2>
        <p className="muted">
          Select a module and configure the session parameters. You will be
          asked timed questions about the module skills. Explain your
          understanding clearly — no solutions are provided.
        </p>

        {error && <p className="defense-error">{error}</p>}

        <div className="defense-form">
          <label className="defense-field">
            <span>Module</span>
            <select
              value={selectedModule}
              onChange={(e) => setSelectedModule(e.target.value)}
            >
              {modules.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.trackTitle} — {m.title} ({m.phase})
                </option>
              ))}
            </select>
          </label>

          <div className="defense-field-row">
            <label className="defense-field">
              <span>Questions</span>
              <select
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>

            <label className="defense-field">
              <span>Time per question</span>
              <select
                value={timeLimit}
                onChange={(e) => setTimeLimit(Number(e.target.value))}
              >
                {[30, 45, 60, 90, 120, 180].map((s) => (
                  <option key={s} value={s}>
                    {s}s
                  </option>
                ))}
              </select>
            </label>
          </div>

          {tmuxSessions.length > 0 && (
            <label className="defense-field">
              <span>Terminal session (optional)</span>
              <select
                value={selectedTmux}
                onChange={(e) => setSelectedTmux(e.target.value)}
              >
                <option value="">None — no terminal context</option>
                {tmuxSessions.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.status}{s.attached ? ", attached" : ""})
                  </option>
                ))}
              </select>
            </label>
          )}

          <button
            className="action-btn"
            onClick={handleStart}
            disabled={loading || !selectedModule}
          >
            {loading ? "Starting..." : "Begin defense"}
          </button>
        </div>
      </section>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Render: Active session                                           */
  /* ---------------------------------------------------------------- */

  if (phase === "active" && currentQuestion) {
    const timerWarning = secondsLeft <= 15 && secondsLeft > 0;
    const timerCritical = secondsLeft <= 5;

    const qaColumn = (
      <div className="defense-qa-column">
        {/* Progress bar */}
        <div className="defense-progress panel">
          <div className="defense-progress-header">
            <span className="eyebrow">
              Question {activeQuestionIndex + 1} of {questions.length}
            </span>
            <span
              className={`defense-timer ${timerWarning ? "defense-timer--warning" : ""} ${timerCritical ? "defense-timer--critical" : ""}`}
            >
              {secondsLeft}s
            </span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{
                width: `${((activeQuestionIndex + 1) / questions.length) * 100}%`,
                backgroundColor: "var(--accent)",
              }}
            />
          </div>
        </div>

        {/* Question */}
        <div className="defense-question panel">
          <div className="defense-question-meta">
            <span className="pill">{currentQuestion.skill}</span>
          </div>
          <p className="defense-question-text">{currentQuestion.text}</p>
        </div>

        {/* Feedback (shown briefly after answering) */}
        {lastFeedback && (
          <div
            className={`defense-feedback panel ${lastFeedback.score >= 0.7 ? "defense-feedback--good" : lastFeedback.score >= 0.4 ? "defense-feedback--partial" : "defense-feedback--low"}`}
          >
            <div className="defense-feedback-header">
              <strong>
                Score: {Math.round(lastFeedback.score * 100)}%
              </strong>
              {lastFeedback.timed_out && (
                <span className="pill pill--in_progress">Timed out</span>
              )}
            </div>
            <p>{lastFeedback.feedback}</p>
          </div>
        )}

        {/* Answer form */}
        {!lastFeedback && (
          <div className="defense-answer panel">
            {error && <p className="defense-error">{error}</p>}
            <label className="defense-field">
              <span>Your explanation</span>
              <textarea
                className="defense-textarea"
                rows={5}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Explain your understanding of this concept in your own words..."
                disabled={submitting}
              />
            </label>
            <button
              className="action-btn"
              onClick={handleSubmitAnswer}
              disabled={submitting || answer.trim().length === 0}
            >
              {submitting ? "Submitting..." : "Submit answer"}
            </button>
          </div>
        )}
      </div>
    );

    return (
      <section className={`defense-active ${selectedTmux ? "defense-active--split" : ""}`}>
        {qaColumn}
        {selectedTmux && (
          <div className="defense-terminal-column">
            <TerminalPane session={selectedTmux} />
          </div>
        )}
      </section>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Render: Results                                                  */
  /* ---------------------------------------------------------------- */

  if (phase === "results" && results) {
    return (
      <section className="defense-results">
        {/* Summary */}
        <div
          className={`defense-results-hero panel ${results.passed ? "defense-results-hero--passed" : "defense-results-hero--failed"}`}
        >
          <p className="eyebrow">Defense complete</p>
          <h2>{results.passed ? "Passed" : "Not passed"}</h2>
          <p className="defense-results-score">
            {Math.round(results.overall_score * 100)}%
          </p>
          <p>{results.summary}</p>
          {results.timed_out_questions > 0 && (
            <p className="muted">
              {results.timed_out_questions} question(s) timed out
            </p>
          )}
        </div>

        {/* Per-question results */}
        <div className="defense-results-list">
          {results.question_results.map((qr, i) => (
            <div
              key={qr.question_id}
              className={`defense-result-card panel ${qr.score >= 0.7 ? "defense-result-card--good" : qr.score >= 0.4 ? "defense-result-card--partial" : "defense-result-card--low"}`}
            >
              <div className="defense-result-header">
                <span className="eyebrow">Question {i + 1}</span>
                <span className="pill">{qr.skill}</span>
              </div>
              <p className="defense-result-question">{qr.question}</p>
              <div className="defense-result-meta">
                <strong>{Math.round(qr.score * 100)}%</strong>
                {qr.timed_out && (
                  <span className="pill pill--in_progress">Timed out</span>
                )}
                {!qr.answered && (
                  <span className="pill pill--todo">Not answered</span>
                )}
                <span className="muted">
                  {qr.elapsed_seconds.toFixed(1)}s
                </span>
              </div>
              <p className="defense-result-feedback">{qr.feedback}</p>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="defense-actions">
          <button className="action-btn" onClick={handleReset}>
            New defense
          </button>
        </div>
      </section>
    );
  }

  /* Fallback: loading or error state */
  return (
    <section className="panel">
      {error ? (
        <>
          <p className="defense-error">{error}</p>
          <button className="action-btn" onClick={handleReset}>
            Try again
          </button>
        </>
      ) : (
        <p className="muted">Loading...</p>
      )}
    </section>
  );
}
