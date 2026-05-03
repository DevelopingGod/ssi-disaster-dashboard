from dotenv import load_dotenv
load_dotenv()  # Must precede any import that reads env vars at module level

import logging
import os
import re
import time as _time
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.graph.graph import compiled_graph
from app.graph.state import AgentState
from app.models.disaster import DisasterEvent


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("disaster-io-api")


# ── Input constraints ────────────────────────────────────────────────────────
_MAX_QUERY_LENGTH    = 600
_MAX_HISTORY_TURNS   = 20   # client can't send more than this many turns
_MAX_TURN_LENGTH     = 800  # chars per history message

# ── In-process rate limiter ──────────────────────────────────────────────────
# Key: client IP (or "unknown").  Value: list of UNIX timestamps of recent calls.
_RATE_WINDOW_SEC  = 60
_RATE_LIMIT_COUNT = 30          # max requests per window per IP
_rate_store: Dict[str, List[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate-limited."""
    now   = _time.time()
    cutoff = now - _RATE_WINDOW_SEC
    calls  = [t for t in _rate_store[ip] if t > cutoff]
    if len(calls) >= _RATE_LIMIT_COUNT:
        return False
    calls.append(now)
    _rate_store[ip] = calls
    return True


def _client_ip(request: Request) -> str:
    """
    Return the real client IP from the TCP connection.

    X-Forwarded-For is intentionally IGNORED — it's a trivially spoofable HTTP
    header that would let any caller forge an arbitrary IP and bypass per-IP
    rate limiting.  We use request.client.host (the actual socket peer address)
    instead.  If this service is ever placed behind a trusted reverse proxy,
    re-introduce XFF only after configuring ProxyHeadersMiddleware with an
    explicit trusted_hosts allowlist.
    """
    return getattr(getattr(request, "client", None), "host", None) or "unknown"


# ── Input sanitisation ───────────────────────────────────────────────────────
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

def _sanitize_str(s: str, max_len: int) -> str:
    return _CONTROL_RE.sub("", s)[:max_len].strip()


# ── Pydantic models ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:  str = Field(default="ok")
    service: str = Field(default="disaster-io-backend")
    version: str = Field(default="0.1.0")


class ChatRequest(BaseModel):
    query:           str            = Field(..., min_length=1, max_length=_MAX_QUERY_LENGTH)
    conversation_id: str | None     = Field(default=None)
    user_id:         str | None     = Field(default=None)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return _sanitize_str(v, _MAX_QUERY_LENGTH)

    @field_validator("conversation_history")
    @classmethod
    def validate_history(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        # Cap depth and sanitise each turn
        trimmed = v[-_MAX_HISTORY_TURNS:]
        cleaned = []
        for turn in trimmed:
            role    = turn.get("role", "")
            content = turn.get("content", "")
            if role not in ("user", "assistant"):
                continue
            cleaned.append({
                "role":    role,
                "content": _sanitize_str(content, _MAX_TURN_LENGTH),
            })
        return cleaned


class ChatResponse(BaseModel):
    response:                 str
    route_target:             str | None = None
    events:                   List[DisasterEvent]      = Field(default_factory=list)
    warnings:                 List[str]                = Field(default_factory=list)
    guardrail_violations:     List[str]                = Field(default_factory=list)
    unavailable_data_reasons: List[str]                = Field(default_factory=list)
    conversation_history:     List[Dict[str, str]]     = Field(default_factory=list)


# ── CORS ─────────────────────────────────────────────────────────────────────

def _cors_origins_from_env() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Disaster.io Backend",
    description="FastAPI + LangGraph orchestration backend for disaster intelligence.",
    version="0.1.0",
)

cors_origins = _cors_origins_from_env()
logger.info("Configured CORS origins: %s", cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    request_id = str(uuid.uuid4())[:8]
    ip         = _client_ip(http_request)

    # ── Rate limit ──────────────────────────────────────────────────────────
    if not _check_rate_limit(ip):
        logger.warning("[%s] Rate limit exceeded for IP %s", request_id, ip)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment before trying again.",
        )

    logger.info("[%s] /chat — ip=%s query=%r", request_id, ip, request.query[:80])

    try:
        # Append the current user turn to history from the client
        incoming_history = list(request.conversation_history)
        incoming_history.append({"role": "user", "content": request.query})

        initial_state = AgentState(
            user_query=request.query,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            conversation_history=incoming_history,
        )

        result      = await compiled_graph.ainvoke(initial_state)
        final_state = AgentState.model_validate(result)

        assistant_reply = (
            final_state.synthesis_summary
            or "No response could be synthesized from available data."
        )

        # Return fully updated history so the client can persist it
        updated_history = list(incoming_history)
        updated_history.append({"role": "assistant", "content": assistant_reply})

        logger.info(
            "[%s] done — route=%s events=%d",
            request_id, final_state.route_target, len(final_state.normalized_events),
        )

        return ChatResponse(
            response=assistant_reply,
            route_target=final_state.route_target,
            events=final_state.normalized_events,
            warnings=final_state.warnings,
            guardrail_violations=final_state.guardrail_violations,
            unavailable_data_reasons=final_state.unavailable_data_reasons,
            conversation_history=updated_history,
        )

    except HTTPException:
        raise  # pass-through our own errors

    except Exception as exc:
        err_str = str(exc)
        logger.error("[%s] Unhandled error: %s", request_id, err_str, exc_info=True)

        if "413" in err_str or "rate_limit" in err_str or "too large" in err_str.lower():
            raise HTTPException(
                status_code=429,
                detail=(
                    "The query returned too many events. Please narrow your search — "
                    "specify a country or a shorter time window and try again."
                ),
            )

        if "temporarily unavailable" in err_str.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Live monitoring feeds are temporarily unavailable. "
                    "Please retry in a moment."
                ),
            )

        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again in a moment.",
        )
