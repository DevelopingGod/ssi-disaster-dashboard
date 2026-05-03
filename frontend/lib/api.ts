import type { ChatRequest, ChatResponse } from "@/lib/types";

const BACKEND_BASE =
  (process.env.NEXT_PUBLIC_BACKEND_CHAT_URL ?? "http://localhost:8000/chat")
    .replace(/\/chat$/, "");

const BACKEND_CHAT_URL    = `${BACKEND_BASE}/chat`;
const BACKEND_HEALTH_URL  = `${BACKEND_BASE}/health`;

/** Fire-and-forget ping so HuggingFace Space wakes before the first real query. */
export function warmBackend(): void {
  fetch(BACKEND_HEALTH_URL, { method: "GET" }).catch(() => {});
}

/**
 * Human-readable message for known HTTP error codes returned by the backend.
 * Falls back to the raw response body for unknown codes.
 */
function _errorMessage(status: number, body: string): string {
  if (status === 429) {
    return "Too many requests — please wait a moment and try again.";
  }
  if (status === 503) {
    return "Live data feeds are temporarily unavailable. Please retry in a moment.";
  }
  if (status === 500) {
    return "The server encountered an unexpected error. Please try again shortly.";
  }
  // Try to extract FastAPI detail string
  try {
    const parsed = JSON.parse(body) as { detail?: string };
    if (parsed.detail) return parsed.detail;
  } catch {
    // ignore
  }
  return `Request failed (${status})`;
}

export async function sendChatQuery(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(BACKEND_CHAT_URL, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(_errorMessage(response.status, body));
  }

  return (await response.json()) as ChatResponse;
}
