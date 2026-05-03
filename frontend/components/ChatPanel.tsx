"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Send, Trash2 } from "lucide-react";

import type { ChatMessage } from "@/lib/types";

const LOADING_MESSAGES = [
  "Querying live GDACS disaster feeds…",
  "Fetching USGS seismic data…",
  "Cross-referencing ReliefWeb reports…",
  "Scanning NASA FIRMS fire detections…",
  "Applying geographic filters…",
  "Routing query to intelligence tools…",
  "Parsing real-time alert data…",
  "Synthesising humanitarian briefing…",
  "Correlating event timelines…",
  "Analysing satellite-derived data…",
  "Running AI synthesis engine…",
  "Compiling crisis intelligence…",
];

function useRotatingMessage(active: boolean, intervalMs = 2600): string {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (!active) { setIndex(0); return; }
    const id = setInterval(
      () => setIndex(i => (i + 1) % LOADING_MESSAGES.length),
      intervalMs,
    );
    return () => clearInterval(id);
  }, [active, intervalMs]);
  return LOADING_MESSAGES[index];
}

type ChatPanelProps = {
  messages: ChatMessage[];
  onSend: (query: string) => Promise<void>;
  onMessageClick: (eventId: string) => void;
  onClearChat: () => void;
  loading: boolean;
  warnings: string[];
  showMap: boolean;
  onToggleMap: () => void;
  /** True once the client has hydrated from localStorage — prevents SSR mismatch */
  mounted?: boolean;
};

export default function ChatPanel({
  messages,
  onSend,
  onMessageClick,
  onClearChat,
  loading,
  warnings,
  showMap,
  onToggleMap,
  mounted = true,
}: ChatPanelProps) {
  const [query, setQuery] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const loadingMessage = useRotatingMessage(loading);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setQuery("");
    await onSend(trimmed);
  };

  const handleClearRequest = () => {
    if (confirmClear) {
      onClearChat();
      setConfirmClear(false);
    } else {
      setConfirmClear(true);
      // Auto-cancel confirmation after 4 s if user doesn't confirm
      setTimeout(() => setConfirmClear(false), 4000);
    }
  };

  return (
    <section
      className="flex h-full flex-col overflow-hidden border-r"
      style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-secondary)" }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between border-b px-4 py-3 flex-shrink-0 gap-2"
        style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-elevated)" }}
      >
        <div className="min-w-0">
          <h1
            className="text-[0.8125rem] font-bold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            Intelligence Agent
          </h1>
          <div className="flex items-center gap-2 mt-0.5">
            <p
              className="text-[0.625rem] font-mono uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              Natural-language disaster queries
            </p>
            <span
              className="text-[0.5rem] font-mono uppercase tracking-widest px-1.5 py-0.5 border"
              style={{
                borderColor: "var(--accent)",
                color: "var(--accent)",
                backgroundColor: "color-mix(in srgb, var(--accent) 8%, transparent)",
              }}
              title="All event timestamps are in Coordinated Universal Time (UTC)"
            >
              UTC
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Clear chat — only rendered after client hydration to avoid SSR mismatch */}
          {mounted && messages.length > 0 && (
            <button
              onClick={handleClearRequest}
              title={confirmClear ? "Click again to confirm clear" : "Clear chat history"}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[0.5625rem] font-mono uppercase tracking-widest border transition-all hover:opacity-90"
              style={
                confirmClear
                  ? {
                      borderColor: "#dc2626",
                      color: "#dc2626",
                      backgroundColor: "color-mix(in srgb, #dc2626 12%, transparent)",
                    }
                  : {
                      borderColor: "var(--border-c)",
                      color: "var(--text-muted)",
                      backgroundColor: "transparent",
                    }
              }
            >
              <Trash2 className="w-3 h-3" />
              {confirmClear ? "Confirm?" : "Clear"}
            </button>
          )}

          <button
            onClick={onToggleMap}
            className="px-3 py-1.5 text-[0.625rem] font-mono uppercase tracking-widest border transition-opacity hover:opacity-75"
            style={{ borderColor: "var(--border-c)", color: "var(--text-secondary)" }}
          >
            {showMap ? "Hide Map" : "Show Map"}
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
        {messages.length === 0 && (
          <div
            className="msg-enter border border-dashed p-5 space-y-3"
            style={{ borderColor: "var(--border-c)", color: "var(--text-muted)" }}
          >
            <p className="font-mono text-[0.625rem] uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Terminal Ready
            </p>
            <p className="text-[0.8125rem] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              Ask me anything about natural disasters — e.g.{" "}
              <span
                className="cursor-pointer underline decoration-dotted underline-offset-2"
                style={{ color: "var(--accent)" }}
                onClick={() => setQuery("Were there any floods in Asia yesterday?")}
              >
                &quot;Were there any floods in Asia yesterday?&quot;
              </span>
            </p>
            <p className="text-[0.5625rem] font-mono" style={{ color: "var(--text-muted)" }}>
              ⏱ All event times are in UTC (Coordinated Universal Time).
            </p>
          </div>
        )}

        {messages.map((message) => {
          const isUser      = message.role === "user";
          const hasEvents   = (message.eventIds?.length ?? 0) > 0;
          const timeLabel   = message.timestamp
            ? new Date(message.timestamp).toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "UTC",
              }) + " UTC"
            : null;

          return (
            <div
              key={message.id}
              onClick={() => {
                if (hasEvents) onMessageClick(message.eventIds![0]);
              }}
              className={`msg-enter flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}
            >
              {/* Role / time row */}
              <div className={`flex items-center gap-2 px-1 ${isUser ? "flex-row-reverse" : ""}`}>
                <span
                  className="text-[0.5rem] font-mono uppercase tracking-widest"
                  style={{ color: "var(--text-muted)" }}
                >
                  {isUser ? "You" : "Agent"}
                </span>
                {timeLabel && (
                  <span
                    className="text-[0.5rem] font-mono"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {timeLabel}
                  </span>
                )}
              </div>

              {/* Bubble */}
              <div
                className={`max-w-[92%] px-4 py-3 text-sm transition-opacity ${
                  hasEvents ? "cursor-pointer hover:opacity-90" : ""
                }`}
                style={
                  isUser
                    ? {
                        backgroundColor: "var(--bg-elevated)",
                        color: "var(--text-primary)",
                        border: "1px solid var(--border-c)",
                        borderRight: "3px solid var(--accent)",
                      }
                    : {
                        backgroundColor: "var(--bg-surface)",
                        color: "var(--text-primary)",
                        border: "1px solid var(--border-c)",
                        borderLeft: "3px solid var(--accent)",
                      }
                }
              >
                {!isUser && (
                  <p
                    className="text-[0.5rem] font-mono uppercase tracking-widest mb-2.5"
                    style={{ color: "var(--accent)" }}
                  >
                    Intelligence Agent
                  </p>
                )}
                <ReactMarkdown
                  components={{
                    h3: ({ ...props }) => (
                      <h3
                        className="text-[0.9375rem] font-bold mt-5 mb-2 tracking-tight"
                        style={{ color: "var(--text-primary)" }}
                        {...props}
                      />
                    ),
                    ul: ({ ...props }) => (
                      <ul
                        className="list-disc pl-5 mb-3 space-y-1.5 text-[0.8125rem]"
                        style={{ color: "var(--text-secondary)" }}
                        {...props}
                      />
                    ),
                    li: ({ ...props }) => (
                      <li className="leading-relaxed" {...props} />
                    ),
                    blockquote: ({ ...props }) => (
                      <blockquote
                        className="border-l-2 pl-4 py-1.5 italic my-3 text-sm"
                        style={{
                          borderColor: "var(--accent)",
                          color: "var(--text-secondary)",
                          backgroundColor: "color-mix(in srgb, var(--accent) 5%, transparent)",
                        }}
                        {...props}
                      />
                    ),
                    p: ({ ...props }) => (
                      <p
                        className="mb-2.5 text-[0.8125rem] leading-[1.65]"
                        style={{ color: isUser ? "var(--text-primary)" : "var(--text-secondary)" }}
                        {...props}
                      />
                    ),
                    strong: ({ ...props }) => (
                      <strong
                        className="font-semibold"
                        style={{ color: "var(--text-primary)" }}
                        {...props}
                      />
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
                {hasEvents && (
                  <p
                    className="mt-2 text-[0.5625rem] font-mono uppercase tracking-wider"
                    style={{ color: "var(--accent)" }}
                  >
                    ↗ Click to highlight on map
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="msg-enter flex flex-col items-start gap-1">
            <span
              className="text-[0.5rem] font-mono uppercase tracking-widest px-1"
              style={{ color: "var(--text-muted)" }}
            >
              Agent
            </span>
            <div
              className="max-w-[92%] flex items-center gap-3 px-4 py-3 border text-[0.75rem] font-mono"
              style={{
                backgroundColor: "var(--bg-surface)",
                borderColor: "var(--border-c)",
                borderLeft: "3px solid var(--accent)",
                color: "var(--text-muted)",
              }}
            >
              <svg
                className="h-3.5 w-3.5 animate-spin flex-shrink-0"
                style={{ color: "var(--accent)" }}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span style={{ color: "var(--text-secondary)" }}>{loadingMessage}</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div
          className="mx-4 mb-3 border px-3 py-2 text-[0.625rem] font-mono"
          style={{
            borderColor: "var(--accent)",
            backgroundColor: "color-mix(in srgb, var(--accent) 8%, transparent)",
            color: "var(--accent)",
          }}
        >
          {warnings.join(" · ")}
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t px-3 py-3.5 flex-shrink-0"
        style={{ borderColor: "var(--border-c)", backgroundColor: "var(--bg-elevated)" }}
      >
        <div className="flex items-center gap-2.5">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about any disaster, anywhere…"
            className="flex-1 px-3.5 py-2.5 text-[0.8125rem] border outline-none transition-all"
            style={{
              backgroundColor: "var(--bg-surface)",
              borderColor: "var(--border-c)",
              color: "var(--text-primary)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.boxShadow = "0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--border-c)";
              e.currentTarget.style.boxShadow = "none";
            }}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="w-10 h-10 flex items-center justify-center transition-all hover:opacity-85 disabled:opacity-35 flex-shrink-0"
            style={{ backgroundColor: "var(--accent)", color: "var(--bg-primary)" }}
            aria-label="Send"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
        <p
          className="mt-2 text-[0.5rem] font-mono uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          Press Enter to send · All times UTC
        </p>
      </form>
    </section>
  );
}
