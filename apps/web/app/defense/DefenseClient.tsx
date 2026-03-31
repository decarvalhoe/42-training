"use client";

import { useEffect, useMemo, useState } from "react";

import {
  GuidedActionButton,
  GuidedBadge,
  GuidedField,
  GuidedPanel,
  GuidedSelect,
  GuidedStatusBar,
  GuidedTextarea,
  GuidedSidebarSection,
} from "@/app/components/GuidedSurface";
import { SidebarContent } from "@/app/components/SidebarSlotProvider";
import { TerminalPane } from "@/app/components/TerminalPane";

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

type QuestionProgress = {
  questionId: string;
  question: string;
  skill: string;
  answer: string;
  score: number;
  feedback: string;
  timedOut: boolean;
  elapsedSeconds: number;
};

type Phase = "setup" | "active" | "results";

type ModuleOption = {
  id: string;
  title: string;
  phase: string;
  trackId: string;
  trackTitle: string;
  skillCount: number;
  deliverable: string;
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
  sourceMode: "live" | "demo";
};

function formatTimer(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function formatFiveScale(score: number) {
  return (score * 5).toFixed(1);
}

function scoreBars(score: number | null) {
  if (score === null) {
    return "░░░░░░░░░░";
  }

  const filled = Math.max(0, Math.min(10, Math.round(score * 10)));
  return `${"█".repeat(filled)}${"░".repeat(10 - filled)}`;
}

export default function DefenseClient({
  modules,
  apiUrl,
  tmuxSessions = [],
  sourceMode,
}: Props) {
  const [selectedModule, setSelectedModule] = useState(modules[0]?.id ?? "");
  const [numQuestions, setNumQuestions] = useState(3);
  const [timeLimit, setTimeLimit] = useState(60);
  const [selectedTmux, setSelectedTmux] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [phase, setPhase] = useState<Phase>("setup");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<DefenseQuestion[]>([]);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [deadline, setDeadline] = useState<Date | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lastFeedback, setLastFeedback] = useState<{
    score: number;
    feedback: string;
    timed_out: boolean;
  } | null>(null);
  const [history, setHistory] = useState<QuestionProgress[]>([]);

  const [results, setResults] = useState<DefenseResultResponse | null>(null);

  const currentModule = modules.find((module) => module.id === selectedModule) ?? modules[0] ?? null;
  const currentQuestion = questions[activeQuestionIndex] ?? null;
  const currentTmux = tmuxSessions.find((session) => session.name === selectedTmux) ?? null;

  useEffect(() => {
    if (phase !== "active" || deadline === null) {
      return;
    }

    const tick = () => {
      const remaining = Math.max(0, Math.ceil((deadline.getTime() - Date.now()) / 1000));
      setSecondsLeft(remaining);
    };

    tick();
    const intervalId = setInterval(tick, 500);
    return () => clearInterval(intervalId);
  }, [phase, deadline]);

  const runningScore = useMemo(() => {
    if (history.length === 0) {
      return null;
    }

    const average = history.reduce((total, item) => total + item.score, 0) / history.length;
    return average;
  }, [history]);

  const breakdown = useMemo(() => {
    return questions.map((question) => {
      const entry = history.find((item) => item.questionId === question.question_id) ?? null;
      return {
        id: question.question_id,
        label: `Q${questions.findIndex((candidate) => candidate.question_id === question.question_id) + 1}`,
        score: entry?.score ?? null,
      };
    });
  }, [history, questions]);

  const evidenceLines = useMemo(() => {
    const lines = [
      `${currentModule?.id ?? "module"} // armed`,
      `${currentModule?.deliverable ?? "deliverable pending"} // target`,
    ];

    if (currentTmux !== null) {
      lines.push(`${currentTmux.name} // ${currentTmux.status}`);
    }

    if (history.length > 0) {
      lines.push(`${history.length} answers // captured`);
    }

    return lines.slice(0, 4);
  }, [currentModule, currentTmux, history.length]);

  async function handleStart() {
    if (!selectedModule || currentModule === null) {
      return;
    }

    setLoading(true);
    setError(null);

    let terminalContext: Record<string, unknown> | undefined;
    if (selectedTmux) {
      try {
        const paneResponse = await fetch(`${apiUrl}/api/v1/tmux/pane/${encodeURIComponent(selectedTmux)}`);
        if (paneResponse.ok) {
          const pane = await paneResponse.json();
          terminalContext = { panes: { [selectedTmux]: pane.content } };
        }
      } catch {
        // Terminal context is optional.
      }
    }

    try {
      const response = await fetch(`${apiUrl}/api/v1/defense/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          track_id: currentModule.trackId,
          module_id: selectedModule,
          phase: currentModule.phase,
          num_questions: numQuestions,
          question_time_limit_seconds: timeLimit,
          ...(terminalContext ? { terminal_context: terminalContext } : {}),
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(body.detail ?? `API error ${response.status}`);
      }

      const data = (await response.json()) as DefenseStartResponse;
      setSessionId(data.session_id);
      setQuestions(data.questions);
      setActiveQuestionIndex(0);
      setAnswer("");
      setLastFeedback(null);
      setResults(null);
      setHistory([]);
      setDeadline(data.current_question_deadline ? new Date(data.current_question_deadline) : null);
      setPhase("active");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to start defense");
    } finally {
      setLoading(false);
    }
  }

  async function fetchResults(currentSessionId: string) {
    const response = await fetch(`${apiUrl}/api/v1/defense/${currentSessionId}/result`);
    if (!response.ok) {
      throw new Error(`Failed to fetch results: ${response.status}`);
    }

    const data = (await response.json()) as DefenseResultResponse;
    setResults(data);
    setPhase("results");
  }

  async function handleSubmitAnswer(answerToSend: string) {
    if (sessionId === null || currentQuestion === null || submitting) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/v1/defense/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestion.question_id,
          answer: answerToSend,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(body.detail ?? `API error ${response.status}`);
      }

      const data = (await response.json()) as DefenseAnswerResponse;

      setHistory((previous) => [
        ...previous,
        {
          questionId: currentQuestion.question_id,
          question: currentQuestion.text,
          skill: currentQuestion.skill,
          answer: answerToSend,
          score: data.score,
          feedback: data.feedback,
          timedOut: data.timed_out,
          elapsedSeconds: data.elapsed_seconds,
        },
      ]);

      setLastFeedback({
        score: data.score,
        feedback: data.feedback,
        timed_out: data.timed_out,
      });

      if (data.questions_remaining === 0) {
        await fetchResults(sessionId);
      } else {
        setTimeout(() => {
          setActiveQuestionIndex((value) => value + 1);
          setAnswer("");
          setLastFeedback(null);
          setDeadline(data.next_question_deadline ? new Date(data.next_question_deadline) : null);
        }, 1800);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }

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
    setHistory([]);
  }

  const sidebarContent = (
    <div className="flex flex-col gap-5">
      <GuidedSidebarSection label="Running score">
        <div className="space-y-1">
          <p className="font-mono text-4xl font-bold text-[var(--shell-warning)]">
            {runningScore === null ? "__ / 5" : `${formatFiveScale(runningScore)} / 5`}
          </p>
          <GuidedBadge tone={sourceMode === "live" ? "success" : "warning"}>
            {sourceMode === "live" ? "API live" : "demo mode"}
          </GuidedBadge>
        </div>
      </GuidedSidebarSection>

      <GuidedSidebarSection label="Breakdown">
        <div className="space-y-1 font-mono text-[10px] leading-5 text-[var(--shell-ink)]">
          {breakdown.length === 0 ? (
            <p>No question started yet</p>
          ) : (
            breakdown.map((entry) => (
              <p key={entry.id}>
                {entry.label} {scoreBars(entry.score)} {entry.score === null ? "___" : `${Math.round(entry.score * 5)}/5`}
              </p>
            ))
          )}
        </div>
      </GuidedSidebarSection>

      <GuidedSidebarSection label="Evidence">
        <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-success)]">
          {evidenceLines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </GuidedSidebarSection>

      <GuidedSidebarSection label="Rules">
        <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-dim)]">
          <p>&gt; {timeLimit}s per question</p>
          <p>&gt; no external docs</p>
          <p>&gt; explain reasoning</p>
          <p>&gt; live answer only</p>
          <p>&gt; minimum 3/5 to pass</p>
        </div>
      </GuidedSidebarSection>

      <GuidedSidebarSection label="Terminal snapshot">
        <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-success)]">
          <p>cwd: {currentTmux?.name ?? "detached"}</p>
          <p>status: {currentTmux?.status ?? "standby"}</p>
          <p>attached: {currentTmux?.attached ? "yes" : "no"}</p>
          <p>answers: {history.length}</p>
        </div>
      </GuidedSidebarSection>
    </div>
  );

  if (phase === "setup") {
    return (
      <div className="grid gap-4">
        <SidebarContent>{sidebarContent}</SidebarContent>
        <div className="grid gap-4">
          <div className="grid gap-4">
            <GuidedPanel className="flex min-h-12 items-center justify-between gap-4 border-[rgba(255,65,65,0.3)] bg-[rgba(255,65,65,0.05)] px-6 py-3">
              <div>
                <p className="font-mono text-[13px] font-bold uppercase tracking-[0.22em] text-[var(--shell-danger)]">
                  Defense // {currentModule?.id ?? "no-module"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-[var(--shell-warning)]">
                  timer: {formatTimer(timeLimit)} / {formatTimer(timeLimit)}
                </span>
                <span className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--shell-ink)]">
                  q 0/{numQuestions}
                </span>
              </div>
            </GuidedPanel>

            <GuidedPanel className="px-6 py-6">
              <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
                oral defense // guided review
              </p>
              <h1 className="mt-4 font-mono text-3xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                Defense and guided review
              </h1>
              <h2 className="mt-6 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                Start a defense session
              </h2>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--shell-muted)]">
                Configure the oral defense exactly once, attach terminal context if needed, then answer timed questions in your own words.
                This flow stays strict on reasoning quality and never falls back to solution-style hints.
              </p>

              {error ? (
                <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-danger)]" role="alert">
                  {error}
                </p>
              ) : null}

              <div className="mt-8 grid gap-4 lg:grid-cols-2">
                <GuidedField label="Module">
                  <GuidedSelect value={selectedModule} onChange={(event) => setSelectedModule(event.target.value)}>
                    {modules.map((module) => (
                      <option key={module.id} value={module.id}>
                        {module.trackTitle} — {module.title} ({module.phase})
                      </option>
                    ))}
                  </GuidedSelect>
                </GuidedField>

                <GuidedField label="Terminal session">
                  <GuidedSelect value={selectedTmux} onChange={(event) => setSelectedTmux(event.target.value)}>
                    <option value="">None — no terminal context</option>
                    {tmuxSessions.map((session) => (
                      <option key={session.name} value={session.name}>
                        {session.name} ({session.status}
                        {session.attached ? ", attached" : ""})
                      </option>
                    ))}
                  </GuidedSelect>
                </GuidedField>

                <GuidedField label="Questions">
                  <GuidedSelect value={numQuestions} onChange={(event) => setNumQuestions(Number(event.target.value))}>
                    {[1, 2, 3, 4, 5].map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </GuidedSelect>
                </GuidedField>

                <GuidedField label="Time per question">
                  <GuidedSelect value={timeLimit} onChange={(event) => setTimeLimit(Number(event.target.value))}>
                    {[30, 45, 60, 90, 120, 180].map((value) => (
                      <option key={value} value={value}>
                        {value}s
                      </option>
                    ))}
                  </GuidedSelect>
                </GuidedField>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <GuidedActionButton onClick={handleStart} disabled={loading || !selectedModule}>
                  {loading ? "Starting..." : "Begin defense"}
                </GuidedActionButton>
              </div>
            </GuidedPanel>
          </div>
        </div>

        <GuidedStatusBar
          left="defense:setup // waiting for launch"
          right={`42-training v1.0 // ${sourceMode === "live" ? "jwt:active" : "demo"}`}
        />
      </div>
    );
  }

  if (phase === "active" && currentQuestion !== null) {
    const timerTone = secondsLeft <= 5 ? "danger" : secondsLeft <= 15 ? "warning" : "default";

    return (
      <div className="grid gap-4">
        <SidebarContent>{sidebarContent}</SidebarContent>
        <div className="grid gap-4">
          <div className="grid gap-4">
            <GuidedPanel className="flex min-h-12 items-center justify-between gap-4 border-[rgba(255,65,65,0.3)] bg-[rgba(255,65,65,0.05)] px-6 py-3">
              <p className="font-mono text-[13px] font-bold uppercase tracking-[0.22em] text-[var(--shell-danger)]">
                Defense // {currentModule?.id ?? "no-module"}
              </p>
              <div className="flex items-center gap-3">
                <GuidedBadge tone={timerTone}>
                  timer: {formatTimer(secondsLeft)} / {formatTimer(timeLimit)}
                </GuidedBadge>
                <span className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--shell-ink)]">
                  q {activeQuestionIndex + 1}/{questions.length}
                </span>
              </div>
            </GuidedPanel>

            <GuidedPanel className="grid min-h-[560px] gap-6 px-6 py-6">
              {history.length > 0 ? (
                <div className="space-y-6 border-b border-[var(--shell-border)] pb-6 font-mono text-[12px] leading-7 text-[var(--shell-dim)]">
                  {history.map((entry) => (
                    <div key={entry.questionId} className="space-y-2">
                      <p className="whitespace-pre-wrap">{`examiner> ${entry.question}`}</p>
                      <p className="whitespace-pre-wrap text-[var(--shell-ink)]">{`learner > ${entry.answer || "[skipped]"}`}</p>
                      <p className="text-[var(--shell-dim)]">{`[SCORE: ${Math.round(entry.score * 5)}/5]`}</p>
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="space-y-5">
                <p className="font-mono text-[14px] font-bold leading-9 text-[var(--shell-success)]">
                  examiner&gt; {currentQuestion.text}
                </p>
                <GuidedTextarea
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="learner > explain how you reason about this question..."
                  disabled={submitting || lastFeedback !== null}
                />
              </div>

              {lastFeedback ? (
                <GuidedPanel
                  className={`px-4 py-4 ${
                    lastFeedback.score >= 0.7
                      ? "border-[rgba(0,224,110,0.35)]"
                      : lastFeedback.score >= 0.4
                        ? "border-[rgba(255,175,0,0.35)]"
                        : "border-[rgba(255,65,65,0.35)]"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <GuidedBadge tone={lastFeedback.score >= 0.7 ? "success" : lastFeedback.score >= 0.4 ? "warning" : "danger"}>
                      score: {Math.round(lastFeedback.score * 100)}%
                    </GuidedBadge>
                    {lastFeedback.timed_out ? <GuidedBadge tone="danger">timed out</GuidedBadge> : null}
                  </div>
                  <p className="mt-4 text-sm leading-7 text-[var(--shell-muted)]">{lastFeedback.feedback}</p>
                </GuidedPanel>
              ) : null}

              {error ? (
                <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-danger)]" role="alert">
                  {error}
                </p>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <GuidedActionButton
                  onClick={() => void handleSubmitAnswer(answer.trim())}
                  disabled={submitting || answer.trim().length === 0 || lastFeedback !== null}
                >
                  {submitting ? "Submitting..." : "Submit"}
                </GuidedActionButton>
                <GuidedActionButton
                  variant="secondary"
                  onClick={() => void handleSubmitAnswer("[skipped by learner]")}
                  disabled={submitting || lastFeedback !== null}
                >
                  Skip
                </GuidedActionButton>
              </div>
            </GuidedPanel>

            {selectedTmux ? (
              <div className="grid gap-4">
                <TerminalPane session={selectedTmux} />
              </div>
            ) : null}
          </div>
        </div>

        <GuidedStatusBar
          left={`defense:active // Q${activeQuestionIndex + 1}/${questions.length} // timer:${secondsLeft}s`}
          right={`42-training v1.0 // ${sourceMode === "live" ? "jwt:active" : "demo"}${selectedTmux ? " // terminal:injected" : ""}`}
        />
      </div>
    );
  }

  if (phase === "results" && results !== null) {
    return (
      <div className="grid gap-4">
        <SidebarContent>{sidebarContent}</SidebarContent>
        <div className="grid gap-4">
          <div className="grid gap-4">
            <GuidedPanel className="flex min-h-12 items-center justify-between gap-4 border-[rgba(255,65,65,0.3)] bg-[rgba(255,65,65,0.05)] px-6 py-3">
              <p className="font-mono text-[13px] font-bold uppercase tracking-[0.22em] text-[var(--shell-danger)]">
                Defense // {currentModule?.id ?? "no-module"}
              </p>
              <GuidedBadge tone={results.passed ? "success" : "danger"}>
                {results.passed ? "passed" : "not passed"}
              </GuidedBadge>
            </GuidedPanel>

            <GuidedPanel className="px-6 py-6">
              <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
                defense complete
              </p>
              <h1 className="mt-4 font-mono text-3xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                {results.passed ? "Defense passed" : "Defense not passed"}
              </h1>
              <p className="mt-4 font-mono text-4xl font-bold text-[var(--shell-warning)]">
                {Math.round(results.overall_score * 100)}%
              </p>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--shell-muted)]">{results.summary}</p>
              {results.timed_out_questions > 0 ? (
                <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-danger)]">
                  {results.timed_out_questions} question(s) timed out
                </p>
              ) : null}

              <div className="mt-8 grid gap-4 lg:grid-cols-2">
                {results.question_results.map((item, index) => (
                  <GuidedPanel key={item.question_id} className="px-4 py-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <GuidedBadge>question {index + 1}</GuidedBadge>
                      <GuidedBadge tone={item.score >= 0.7 ? "success" : item.score >= 0.4 ? "warning" : "danger"}>
                        {Math.round(item.score * 100)}%
                      </GuidedBadge>
                      <GuidedBadge>{item.skill}</GuidedBadge>
                    </div>
                    <p className="mt-4 font-mono text-sm leading-7 text-[var(--shell-ink)]">{item.question}</p>
                    <p className="mt-4 text-sm leading-7 text-[var(--shell-muted)]">{item.feedback}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {item.timed_out ? <GuidedBadge tone="danger">timed out</GuidedBadge> : null}
                      {!item.answered ? <GuidedBadge tone="warning">not answered</GuidedBadge> : null}
                      <GuidedBadge>{item.elapsed_seconds.toFixed(1)}s</GuidedBadge>
                    </div>
                  </GuidedPanel>
                ))}
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                <GuidedActionButton onClick={handleReset}>New defense</GuidedActionButton>
              </div>
            </GuidedPanel>
          </div>
        </div>

        <GuidedStatusBar
          left={`defense:complete // score:${Math.round(results.overall_score * 100)}%`}
          right={`42-training v1.0 // ${sourceMode === "live" ? "jwt:active" : "demo"}`}
        />
      </div>
    );
  }

  return (
    <GuidedPanel className="px-6 py-6">
      {error ? (
        <>
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-danger)]">{error}</p>
          <div className="mt-4">
            <GuidedActionButton onClick={handleReset}>Try again</GuidedActionButton>
          </div>
        </>
      ) : (
        <p className="font-mono text-sm text-[var(--shell-muted)]">Loading...</p>
      )}
    </GuidedPanel>
  );
}
