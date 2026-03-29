"use client";

import { useCallback, useRef, useState } from "react";

import { SourcePolicyBadge } from "@/app/components/SourcePolicyBadge";
import { TerminalPane } from "@/app/components/TerminalPane";

type Module = {
  id: string;
  title: string;
  phase: string;
  trackId: string;
  trackTitle: string;
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

const CONFIDENCE_CLASS: Record<string, string> = {
  high: "defense-feedback--good",
  medium: "defense-feedback--partial",
  low: "defense-feedback--low",
};

export default function MentorClient({
  modules,
  gatewayUrl,
  activeSession,
}: {
  modules: Module[];
  gatewayUrl: string;
  activeSession: string | null;
}) {
  const [selectedModule, setSelectedModule] = useState(modules[0]?.id ?? "");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTerminal, setShowTerminal] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const currentModule = modules.find((m) => m.id === selectedModule);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }, 50);
  }, []);

  const sendMessage = useCallback(async () => {
    const trimmed = question.trim();
    if (!trimmed || trimmed.length < 3 || loading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setError(null);
    setLoading(true);
    scrollToBottom();

    try {
      const res = await fetch(`${gatewayUrl}/api/v1/mentor/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          track_id: currentModule?.trackId ?? "shell",
          module_id: selectedModule || undefined,
          question: trimmed,
          pace_mode: "normal",
          phase: currentModule?.phase ?? "foundation",
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `API error ${res.status}`);
      }

      const data = (await res.json()) as MentorResponseData;

      const mentorMsg: Message = {
        id: `m-${Date.now()}`,
        role: "mentor",
        content: data.observation,
        response: data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, mentorMsg]);
      scrollToBottom();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [question, loading, selectedModule, currentModule, gatewayUrl, scrollToBottom]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="mentor-layout">
      <section className="mentor-sidebar panel">
        <div className="defense-field">
          <label htmlFor="mentor-module">Module context</label>
          <select
            id="mentor-module"
            value={selectedModule}
            onChange={(e) => setSelectedModule(e.target.value)}
          >
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.trackTitle} / {m.title}
              </option>
            ))}
          </select>
        </div>

        {currentModule && (
          <div className="mentor-context">
            <p className="eyebrow">Context</p>
            <p>
              <strong>Track:</strong> {currentModule.trackTitle}
            </p>
            <p>
              <strong>Phase:</strong> {currentModule.phase}
            </p>
          </div>
        )}

        {activeSession && (
          <div className="mentor-terminal-toggle">
            <button
              className="action-btn"
              onClick={() => setShowTerminal((p) => !p)}
            >
              {showTerminal ? "Hide terminal" : "Show terminal"}
            </button>
          </div>
        )}

        {showTerminal && activeSession && (
          <TerminalPane session={activeSession} />
        )}
      </section>

      <section className="mentor-chat panel">
        <div ref={scrollRef} className="mentor-messages">
          {messages.length === 0 && (
            <div className="mentor-empty">
              <p className="muted">
                Ask a question about the current module. The mentor follows the 42
                philosophy: observations, questions and hints — not direct answers.
              </p>
            </div>
          )}

          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="mentor-msg mentor-msg--user">
                <p>{msg.content}</p>
              </div>
            ) : (
              <div
                key={msg.id}
                className={`mentor-msg mentor-msg--mentor ${CONFIDENCE_CLASS[msg.response?.confidence_level ?? "medium"]}`}
              >
                <div className="mentor-response">
                  <div className="mentor-field">
                    <p className="eyebrow">Observation</p>
                    <p>{msg.response?.observation}</p>
                  </div>
                  <div className="mentor-field">
                    <p className="eyebrow">Question</p>
                    <p>{msg.response?.question}</p>
                  </div>
                  <div className="mentor-field">
                    <p className="eyebrow">Hint</p>
                    <p>{msg.response?.hint}</p>
                  </div>
                  <div className="mentor-field">
                    <p className="eyebrow">Next action</p>
                    <p>{msg.response?.next_action}</p>
                  </div>
                </div>

                {msg.response && msg.response.sources_used.length > 0 && (
                  <div className="mentor-sources">
                    <p className="eyebrow">Sources used</p>
                    <div className="mentor-sources-list">
                      {msg.response.sources_used.map((s, i) => (
                        <span key={`${msg.id}-src-${i}`} className="mentor-source-item">
                          <SourcePolicyBadge tier={s.tier} />
                          {s.url ? (
                            <a href={s.url} target="_blank" rel="noreferrer" className="mentor-source-link">
                              {s.label}
                            </a>
                          ) : (
                            <span className="muted">{s.label}</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mentor-meta">
                  <span className={`spb spb--${msg.response?.confidence_level === "high" ? "high" : msg.response?.confidence_level === "medium" ? "medium" : "low"}`}>
                    Confidence: {msg.response?.confidence_level}
                  </span>
                  {msg.response?.direct_solution_allowed && (
                    <span className="pill pill--in_progress">Direct solutions allowed</span>
                  )}
                </div>
              </div>
            )
          )}

          {loading && (
            <div className="mentor-msg mentor-msg--loading">
              <p className="muted">Thinking...</p>
            </div>
          )}
        </div>

        {error && <div className="defense-error">{error}</div>}

        <div className="mentor-input">
          <textarea
            className="defense-textarea"
            placeholder="Ask a question (Shift+Enter for newline)..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            rows={2}
          />
          <button
            className="action-btn"
            onClick={sendMessage}
            disabled={loading || question.trim().length < 3}
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </div>
      </section>
    </div>
  );
}
