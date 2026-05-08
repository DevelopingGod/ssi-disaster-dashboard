"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

import ChatPanel from "@/components/ChatPanel";
import { sendChatQuery, warmBackend } from "@/lib/api";
import type { ChatMessage, ConversationTurn, DisasterEvent } from "@/lib/types";

const MapPanel = dynamic(() => import("@/components/MapPanel"), { ssr: false });

const MOBILE_BREAKPOINT = 768;

// ── Storage helpers ──────────────────────────────────────────────────────────
const SK = {
  messages:  "disaster-io:messages",
  events:    "disaster-io:events",
  history:   "disaster-io:history",
  showMap:   "disaster-io:showMap",
  chatWidth: "disaster-io:chatWidth",
};

const CHAT_WIDTH_MIN = 260;
const CHAT_WIDTH_MAX = 720;
const CHAT_WIDTH_DEFAULT = 420;

function loadJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Quota exceeded — silently ignore
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  // `mounted` prevents localStorage-dependent state from causing SSR/client hydration mismatches.
  const [mounted, setMounted] = useState(false);

  const [messages, setMessages]               = useState<ChatMessage[]>([]);
  const [events, setEvents]                   = useState<DisasterEvent[]>([]);
  const [warnings, setWarnings]               = useState<string[]>([]);
  const [loading, setLoading]                 = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [showMap, setShowMap]                 = useState(true);
  const [chatWidth, setChatWidth]             = useState(CHAT_WIDTH_DEFAULT);
  const [isMobile, setIsMobile]               = useState(false);

  // Conversation history ref — no re-render on change; synced to localStorage after mount
  const conversationHistoryRef = useRef<ConversationTurn[]>([]);

  // Resize state — all in refs so mouse handlers don't need re-registration
  const isDragging   = useRef(false);
  const dragStartX   = useRef(0);
  const dragStartW   = useRef(CHAT_WIDTH_DEFAULT);

  const conversationId = "local-session";

  // ── Hydrate from localStorage once on client mount ───────────────────────
  useEffect(() => {
    const storedMessages = loadJson<ChatMessage[]>(SK.messages, []);
    setMessages(storedMessages);
    setEvents(loadJson<DisasterEvent[]>(SK.events, []));
    // On mobile always start on chat — don't restore a desktop "map open" state
    const mobileNow = window.innerWidth < MOBILE_BREAKPOINT;
    setShowMap(mobileNow ? false : loadJson<boolean>(SK.showMap, true));
    setChatWidth(loadJson<number>(SK.chatWidth, CHAT_WIDTH_DEFAULT));
    conversationHistoryRef.current = loadJson<ConversationTurn[]>(SK.history, []);
    setMounted(true);
    warmBackend();

    // Auto-load global situation on fresh sessions (no stored messages)
    if (storedMessages.length === 0) {
      void handleAutoLoad();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Persist to localStorage whenever state changes (after mount) ─────────
  useEffect(() => { if (mounted) saveJson(SK.messages,  messages);  }, [mounted, messages]);
  useEffect(() => { if (mounted) saveJson(SK.events,    events);    }, [mounted, events]);
  useEffect(() => { if (mounted) saveJson(SK.showMap,   showMap);   }, [mounted, showMap]);
  useEffect(() => { if (mounted) saveJson(SK.chatWidth, chatWidth); }, [mounted, chatWidth]);

  // ── Mobile detection ─────────────────────────────────────────────────────
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    check(); // Run immediately on mount
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // ── Resize listeners (document-level, stable refs) ───────────────────────
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta  = e.clientX - dragStartX.current;
      const clamped = Math.min(
        Math.max(dragStartW.current + delta, CHAT_WIDTH_MIN),
        Math.min(CHAT_WIDTH_MAX, window.innerWidth * 0.72),
      );
      setChatWidth(Math.round(clamped));
    };

    const onUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor    = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup",   onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup",   onUp);
    };
  }, []); // stable — uses only refs

  const onResizeStart = (e: React.MouseEvent) => {
    isDragging.current  = true;
    dragStartX.current  = e.clientX;
    dragStartW.current  = chatWidth;
    document.body.style.cursor     = "col-resize";
    document.body.style.userSelect = "none";
    e.preventDefault();
  };

  // ── Handlers ─────────────────────────────────────────────────────────────

  /**
   * Auto-load: fired once on a fresh session (no stored messages).
   * Fetches the current global disaster situation without requiring the user
   * to type anything.  Does NOT add a user message bubble — the agent speaks
   * first, like a good intelligence briefing.
   */
  const handleAutoLoad = async () => {
    const AUTO_QUERY =
      "What natural disasters are currently active or have occurred worldwide in the past week? Give me a full global briefing.";

    // Show an immediate "thinking" state so the UI isn't silent
    const placeholderId = crypto.randomUUID();
    setMessages([
      {
        id:        placeholderId,
        role:      "assistant",
        content:   "Fetching the latest global disaster intelligence — scanning live feeds worldwide…",
        timestamp: nowIso(),
      },
    ]);
    setLoading(true);

    try {
      const data = await sendChatQuery({
        query:                AUTO_QUERY,
        conversation_id:      conversationId,
        conversation_history: [],
      });

      if (data.conversation_history?.length) {
        conversationHistoryRef.current = data.conversation_history;
        saveJson(SK.history, data.conversation_history);
      }

      const newEvents = data.events ?? [];
      setEvents(newEvents);
      setWarnings([
        ...data.warnings,
        ...data.guardrail_violations,
        ...data.unavailable_data_reasons,
      ]);

      const responseMessage: ChatMessage = {
        id:        crypto.randomUUID(),
        role:      "assistant",
        content:   data.response,
        timestamp: nowIso(),
        eventIds:  newEvents.map((e) => e.event_id),
      };
      // Replace the placeholder with the real response
      setMessages([responseMessage]);
      saveJson(SK.messages, [responseMessage]);
    } catch (error) {
      const err = error instanceof Error ? error.message : "Unknown error";
      const errMessage: ChatMessage = {
        id:        crypto.randomUUID(),
        role:      "assistant",
        content:   `Could not load initial disaster briefing: ${err}. You can still ask me anything below.`,
        timestamp: nowIso(),
      };
      setMessages([errMessage]);
      setWarnings(["Initial load failed — backend may be starting up. Try asking a question."]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (query: string) => {
    const userMessage: ChatMessage = {
      id:        crypto.randomUUID(),
      role:      "user",
      content:   query,
      timestamp: nowIso(),
    };
    setMessages((prev) => [...prev, userMessage]);
    // Clear the map immediately so stale pins from the previous query don't
    // sit on screen while the new request is in flight.
    setEvents([]);
    setWarnings([]);
    setSelectedEventId(null);
    setLoading(true);

    try {
      const data = await sendChatQuery({
        query,
        conversation_id:      conversationId,
        conversation_history: conversationHistoryRef.current,
      });

      // Server echoes back the fully-updated history (user + assistant appended)
      if (data.conversation_history?.length) {
        conversationHistoryRef.current = data.conversation_history;
        saveJson(SK.history, data.conversation_history);
      }

      const newEvents = data.events ?? [];
      setEvents(newEvents);
      setWarnings([
        ...data.warnings,
        ...data.guardrail_violations,
        ...data.unavailable_data_reasons,
      ]);

      const assistantMessage: ChatMessage = {
        id:        crypto.randomUUID(),
        role:      "assistant",
        content:   data.response,
        timestamp: nowIso(),
        eventIds:  newEvents.map((e) => e.event_id),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setSelectedEventId(null);
    } catch (error) {
      const err = error instanceof Error ? error.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        {
          id:        crypto.randomUUID(),
          role:      "assistant",
          content:   `Request failed: ${err}`,
          timestamp: nowIso(),
        },
      ]);
      setWarnings(["Unable to contact backend service."]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setEvents([]);
    setWarnings([]);
    setSelectedEventId(null);
    conversationHistoryRef.current = [];
    // Clear all persisted session keys
    Object.values(SK).forEach((key) => {
      try { localStorage.removeItem(key); } catch { /* noop */ }
    });
  };

  // ── Shared props for ChatPanel ───────────────────────────────────────────
  const chatPanelProps = {
    messages,
    onSend:        handleSend,
    onClearChat:   handleClearChat,
    loading,
    warnings,
    mounted,
  };

  // ── Mobile layout — full-screen tab switch (chat OR map) ─────────────────
  if (isMobile) {
    return (
      <main
        className="flex w-full overflow-hidden"
        style={{ height: "calc(100vh - 56px)", backgroundColor: "var(--bg-primary)" }}
      >
        {showMap ? (
          /*
           * Fixed full-viewport overlay. Nav bar sits at the TOP (never
           * cut off by Android system navigation). Map fills below it.
           */
          <div
            style={{
              position: "fixed",
              top: 0, left: 0, right: 0, bottom: 0,
              zIndex: 9999,
              background: "var(--bg-primary)",
            }}
          >
            {/* TOP bar — always the first thing the user sees */}
            <div
              style={{
                position: "absolute",
                top: 0, left: 0, right: 0,
                height: "52px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 1rem",
                backgroundColor: "var(--bg-elevated)",
                borderBottom: "1px solid var(--border-c)",
                zIndex: 10000,
              }}
            >
              <button
                onClick={() => setShowMap(false)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.5rem 1rem",
                  border: "1px solid var(--accent)",
                  color: "var(--accent)",
                  backgroundColor: "color-mix(in srgb, var(--accent) 10%, transparent)",
                  fontFamily: "monospace",
                  fontSize: "0.625rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  cursor: "pointer",
                }}
              >
                ← Back to Chat
              </button>
              <span
                style={{
                  fontFamily: "monospace",
                  fontSize: "0.5rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: "var(--text-muted)",
                }}
              >
                {events.length} event{events.length !== 1 ? "s" : ""} plotted
              </span>
            </div>

            {/* Map: everything below the top bar */}
            <div
              style={{
                position: "absolute",
                top: "52px", left: 0, right: 0, bottom: 0,
                overflow: "hidden",
              }}
            >
              <MapPanel events={events} selectedEventId={selectedEventId} isMobile />
            </div>
          </div>
        ) : (
          /* Full-screen chat; toggle button switches to map view */
          <div className="h-full w-full overflow-hidden">
            <ChatPanel
              {...chatPanelProps}
              showMap={false}
              onToggleMap={() => setShowMap(true)}
              onMessageClick={(id) => {
                setSelectedEventId(id);
                setShowMap(true); // Auto-switch to map when a pinned event is tapped
              }}
            />
          </div>
        )}
      </main>
    );
  }

  // ── Desktop layout — resizable split grid ────────────────────────────────
  return (
    <main
      className="flex w-full overflow-hidden"
      style={{
        height: "calc(100vh - 56px)",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      {showMap ? (
        /* ── Split view: resizable chat | drag handle | map ── */
        <div
          className="h-full w-full overflow-hidden"
          style={{
            display: "grid",
            gridTemplateColumns: `${chatWidth}px 5px 1fr`,
            gridTemplateRows:    "1fr",
          }}
        >
          {/* Chat panel */}
          <div className="h-full overflow-hidden min-w-0">
            <ChatPanel
              {...chatPanelProps}
              showMap={showMap}
              onToggleMap={() => setShowMap(false)}
              onMessageClick={setSelectedEventId}
            />
          </div>

          {/* Drag handle */}
          <div
            onMouseDown={onResizeStart}
            className="h-full flex-shrink-0 resize-handle"
            title="Drag to resize"
            style={{ backgroundColor: "var(--border-c)", cursor: "col-resize" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "var(--accent)";
            }}
            onMouseLeave={(e) => {
              if (!isDragging.current)
                e.currentTarget.style.backgroundColor = "var(--border-c)";
            }}
          />

          {/* Map panel */}
          <div className="h-full overflow-hidden min-w-0">
            <MapPanel events={events} selectedEventId={selectedEventId} />
          </div>
        </div>
      ) : (
        /* ── Chat-only view ── */
        <div className="h-full w-full overflow-hidden">
          <ChatPanel
            {...chatPanelProps}
            showMap={showMap}
            onToggleMap={() => setShowMap(true)}
            onMessageClick={setSelectedEventId}
          />
        </div>
      )}
    </main>
  );
}
