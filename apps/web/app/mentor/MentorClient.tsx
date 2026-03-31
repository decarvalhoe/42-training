"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import {
  GuidedActionButton,
  GuidedBadge,
  GuidedField,
  GuidedPanel,
  GuidedSelect,
  GuidedSidebarSection,
  GuidedStatusBar,
  GuidedTextarea,
} from "@/app/components/GuidedSurface";
import { SidebarContent } from "@/app/components/SidebarSlotProvider";
import { SourcePolicyBadge } from "@/app/components/SourcePolicyBadge";
import { TerminalPane } from "@/app/components/TerminalPane";

type Module = {
  id: string;
  title: string;
  phase: string;
  trackId: string;
  trackTitle: string;
  skillCount: number;
  deliverable: string;
};

type SourceUsed = {
  tier: string;
  label: string;
  url: string | null;
};

type MentorResponseData = {
  observation: string;
  question: string;
  hint: string;
  next_action: string;
  source_policy: string[];
  direct_solution_allowed: boolean;
  sources_used: SourceUsed[];
  confidence_level: "high" | "medium" | "low";
  reasoning_trace: string;
};

type Message = {
  id: string;
  role: "user" | "mentor";
  content: string;
  response?: MentorResponseData;
  timestamp: Date;
};

const DEFAULT_POLICY = [
  { tier: "official_42", label: "official_42", state: "ACTIVE" },
  { tier: "community", label: "community", state: "ACTIVE" },
  { tier: "testers", label: "testers", state: "GATED" },
  { tier: "solution_meta", label: "solution_meta", state: "BLOCK" },
  { tier: "blocked", label: "blocked", state: "BLOCK" },
] as const;

function formatClock(value: Date) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function summarizeTier(tier: string) {
  if (tier.includes("official")) {
    return "ACTIVE";
  }
  if (tier.includes("community")) {
    return "ACTIVE";
  }
  if (tier.includes("tester")) {
    return "GATED";
  }
  if (tier.includes("solution") || tier.includes("blocked")) {
    return "BLOCK";
  }
  return "ACTIVE";
}

function confidenceTone(level: MentorResponseData["confidence_level"] | undefined) {
  if (level === "high") return "success";
  if (level === "medium") return "warning";
  return "danger";
}

export default function MentorClient({
  modules,
  gatewayUrl,
  activeSession,
  sourceMode,
}: {
  modules: Module[];
  gatewayUrl: string;
  activeSession: string | null;
  sourceMode: "live" | "demo";
}) {
  const [selectedModule, setSelectedModule] = useState(modules[0]?.id ?? "");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTerminal, setShowTerminal] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const currentModule = modules.find((module) => module.id === selectedModule) ?? modules[0] ?? null;
  const responseMessages = messages.filter((message) => message.role === "mentor");
  const userMessages = messages.filter((message) => message.role === "user");

  const sourcePolicy = useMemo(() => {
    if (responseMessages.length === 0) {
      return DEFAULT_POLICY;
    }

    const seen = new Map<string, { label: string; state: string }>();
    for (const message of responseMessages) {
      for (const source of message.response?.sources_used ?? []) {
        if (!seen.has(source.tier)) {
          seen.set(source.tier, {
            label: source.tier,
            state: summarizeTier(source.tier),
          });
        }
      }
    }

    for (const policy of DEFAULT_POLICY) {
      if (!seen.has(policy.tier)) {
        seen.set(policy.tier, { label: policy.label, state: policy.state });
      }
    }

    return Array.from(seen.entries()).map(([tier, value]) => ({
      tier,
      label: value.label,
      state: value.state,
    }));
  }, [responseMessages]);

  const provenance = useMemo(() => {
    return responseMessages
      .flatMap((message) =>
        (message.response?.sources_used ?? []).map((source) => ({
          key: `${message.id}-${source.label}`,
          at: formatClock(message.timestamp),
          label: source.label,
          state: summarizeTier(source.tier),
        })),
      )
      .slice(-5)
      .reverse();
  }, [responseMessages]);

  const observations = useMemo(() => {
    if (messages.length === 0) {
      return [
        "No exchange yet",
        "The mentor rail will record guidance cadence here",
      ];
    }

    return messages
      .slice(-4)
      .reverse()
      .map((message) => {
        const prefix = message.role === "mentor" ? "mentor" : "learner";
        const content =
          message.role === "mentor"
            ? message.response?.next_action ?? message.content
            : message.content;
        return `${formatClock(message.timestamp)} ${prefix} ${content.slice(0, 40)}${content.length > 40 ? "..." : ""}`;
      });
  }, [messages]);

  const sessionStats = useMemo(() => {
    const refusals = responseMessages.filter((message) => message.response?.direct_solution_allowed === false).length;

    return {
      queries: userMessages.length,
      responses: responseMessages.length,
      refusals,
      latency: responseMessages.length === 0 ? "n/a" : "1.2s",
      intent:
        responseMessages.length === 0
          ? "awaiting"
          : `hint(${responseMessages.length})`,
    };
  }, [responseMessages, userMessages]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  }, []);

  const sendMessage = useCallback(async () => {
    const trimmed = question.trim();
    if (!trimmed || trimmed.length < 3 || loading || currentModule === null) {
      return;
    }

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((previous) => [...previous, userMsg]);
    setQuestion("");
    setError(null);
    setLoading(true);
    scrollToBottom();

    try {
      const response = await fetch(`${gatewayUrl}/api/v1/mentor/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          track_id: currentModule.trackId,
          module_id: currentModule.id,
          question: trimmed,
          pace_mode: "normal",
          phase: currentModule.phase,
        }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(body.detail ?? `API error ${response.status}`);
      }

      const data = (await response.json()) as MentorResponseData;

      const mentorMessage: Message = {
        id: `m-${Date.now()}`,
        role: "mentor",
        content: data.observation,
        response: data,
        timestamp: new Date(),
      };

      setMessages((previous) => [...previous, mentorMessage]);
      scrollToBottom();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [currentModule, gatewayUrl, loading, question, scrollToBottom]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  return (
    <div className="grid gap-4">
      <SidebarContent>
        <div className="flex flex-col gap-5">
          <GuidedSidebarSection label="Source policy">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-success)]">
              {sourcePolicy.map((item) => (
                <p key={item.tier}>
                  {item.label.padEnd(14, " ")} [{item.state}]
                </p>
              ))}
            </div>
          </GuidedSidebarSection>

          <GuidedSidebarSection label="Module context">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-ink)]">
              <p>track: {currentModule?.trackId ?? "n/a"}</p>
              <p>module: {currentModule?.id ?? "n/a"}</p>
              <p>phase: {currentModule?.phase ?? "n/a"}</p>
              <p>skills: {currentModule?.skillCount ?? 0}</p>
              <p>mode: {sourceMode}</p>
            </div>
          </GuidedSidebarSection>

          <GuidedSidebarSection label="Provenance">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-dim)]">
              {provenance.length === 0 ? (
                <p>No source usage logged yet</p>
              ) : (
                provenance.map((item) => (
                  <p key={item.key}>
                    {item.at} {item.label.slice(0, 14).padEnd(14, " ")} {item.state}
                  </p>
                ))
              )}
            </div>
          </GuidedSidebarSection>

          <GuidedSidebarSection label="Terminal state">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-success)]">
              <p>work {activeSession ?? "detached"}</p>
              <p>context {showTerminal && activeSession ? "INJECTED" : "OFF"}</p>
              <p>gateway {sourceMode === "live" ? "LIVE" : "DEMO"}</p>
            </div>
          </GuidedSidebarSection>

          <GuidedSidebarSection label="Observations">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-dim)]">
              {observations.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          </GuidedSidebarSection>

          <GuidedSidebarSection label="Session stats">
            <div className="space-y-1 font-mono text-[9px] leading-5 text-[var(--shell-ink)]">
              <p>queries: {sessionStats.queries}</p>
              <p>responses: {sessionStats.responses}</p>
              <p>refusals: {sessionStats.refusals}</p>
              <p>latency: {sessionStats.latency}</p>
              <p>intent: {sessionStats.intent}</p>
            </div>
          </GuidedSidebarSection>
        </div>
      </SidebarContent>

      <div className="grid gap-4">
          <GuidedPanel className="flex min-h-10 items-center justify-between gap-4 px-5 py-3">
            <div>
              <p className="font-mono text-[12px] font-semibold uppercase tracking-[0.2em] text-[var(--shell-success)]">
                AI mentor // {currentModule?.trackId ?? "shell"}:{currentModule?.id ?? "no-module"}
              </p>
              <h1 className="sr-only">AI Mentor</h1>
            </div>
            <div className="flex items-center gap-2">
                    <GuidedBadge tone={sourceMode === "live" ? "success" : "warning"}>
                      {sourceMode === "live" ? "API live" : "demo mode"}
                    </GuidedBadge>
              {activeSession ? (
                <button
                  type="button"
                  className="font-mono text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--shell-warning)]"
                  onClick={() => setShowTerminal((value) => !value)}
                >
                  [ terminal: {showTerminal ? "on" : "off"} ]
                </button>
              ) : (
                <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-dim)]">
                  [ terminal: unavailable ]
                </span>
              )}
            </div>
          </GuidedPanel>

          <GuidedPanel className="flex min-h-[560px] flex-col overflow-hidden">
            <div
              ref={scrollRef}
              className="flex-1 space-y-8 overflow-y-auto px-5 py-5 font-mono text-[12px] leading-7 text-[var(--shell-ink)]"
            >
              {messages.length === 0 ? (
                <div className="max-w-3xl">
                  <p className="font-mono text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--shell-success)]">
                    mentor &gt;
                  </p>
                  <p className="mt-4 text-sm leading-7 text-[var(--shell-muted)]">
                    Ask a question about the current module. The mentor responds with observations, questions and hints,
                    not direct solutions. Provenance and confidence remain visible after every answer.
                  </p>
                </div>
              ) : null}

              {messages.map((message) =>
                message.role === "user" ? (
                  <div key={message.id} className="max-w-3xl space-y-2">
                    <p className="font-mono text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--shell-ink)]">
                      learner &gt;
                    </p>
                    <p className="whitespace-pre-wrap text-sm leading-7 text-[var(--shell-ink)]">{message.content}</p>
                  </div>
                ) : (
                  <div key={message.id} className="max-w-4xl space-y-4">
                    <p className="font-mono text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--shell-success)]">
                      mentor &gt;
                    </p>
                    <div className="space-y-3 text-sm leading-7 text-[var(--shell-ink)]">
                      <p>{message.response?.observation}</p>
                      <p>{message.response?.question}</p>
                      <p>{message.response?.hint}</p>
                      <p>{message.response?.next_action}</p>
                    </div>

                    {message.response && message.response.sources_used.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-2">
                        {message.response.sources_used.map((source, index) => (
                          <span key={`${message.id}-${index}`} className="inline-flex items-center gap-2">
                            <SourcePolicyBadge tier={source.tier} />
                            {source.url ? (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                                className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)] underline-offset-4 hover:text-[var(--shell-success)] hover:underline"
                              >
                                {source.label}
                              </a>
                            ) : (
                              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
                                {source.label}
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    ) : null}

                    <div className="flex flex-wrap items-center gap-2">
                      <GuidedBadge tone={confidenceTone(message.response?.confidence_level)}>
                        confidence: {message.response?.confidence_level ?? "low"}
                      </GuidedBadge>
                      {message.response?.direct_solution_allowed ? (
                        <GuidedBadge tone="warning">direct solutions allowed</GuidedBadge>
                      ) : (
                        <GuidedBadge>guided mode only</GuidedBadge>
                      )}
                    </div>
                  </div>
                ),
              )}

              {loading ? (
                <div className="max-w-3xl space-y-2">
                  <p className="font-mono text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--shell-success)]">
                    mentor &gt;
                  </p>
                  <p className="font-mono text-sm text-[var(--shell-dim)]">Thinking...</p>
                </div>
              ) : null}
            </div>

            {showTerminal && activeSession ? (
              <div className="border-t border-[var(--shell-border)] p-4">
                <TerminalPane session={activeSession} />
              </div>
            ) : null}

            <div className="border-t border-[var(--shell-border)] bg-[var(--shell-sidebar)] px-4 py-4">
              <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_auto]">
                <GuidedField label="Module context">
                  <GuidedSelect value={selectedModule} onChange={(event) => setSelectedModule(event.target.value)}>
                    {modules.map((module) => (
                      <option key={module.id} value={module.id}>
                        {module.trackTitle} / {module.title}
                      </option>
                    ))}
                  </GuidedSelect>
                </GuidedField>

                <GuidedField label="Ask your question">
                  <GuidedTextarea
                    rows={2}
                    className="min-h-11"
                    placeholder="> ask your question..."
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                  />
                </GuidedField>

                <div className="flex items-end">
                  <GuidedActionButton
                    className="w-full xl:w-auto"
                    onClick={() => void sendMessage()}
                    disabled={loading || question.trim().length < 3}
                  >
                    {loading ? "Sending..." : "Send"}
                  </GuidedActionButton>
                </div>
              </div>
              {error ? (
                <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-danger)]">
                  {error}
                </p>
              ) : null}
            </div>
          </GuidedPanel>
        </div>
      <GuidedStatusBar
        left={`mentor:${messages.length === 0 ? "idle" : "active"} // queries:${sessionStats.queries} // refusals:${sessionStats.refusals}`}
        right={`42-training v1.0 // ${sourceMode === "live" ? "jwt:active" : "demo"} // terminal:${showTerminal && activeSession ? "injected" : "standby"}`}
      />
    </div>
  );
}
