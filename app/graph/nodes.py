import json
import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.graph.state import AgentState
from app.graph.tools import fetch_live_disasters, search_historical_events, fetch_humanitarian_context
from app.models.disaster import DisasterEvent


# ── Geographic scope → country name set ─────────────────────────────────────
# Used in synthesis_node to trim normalized_events to only the countries that
# belong to the requested continent/region, so the map stays geographically
# focused instead of plotting every event fetched globally.
# Keys are lowercase; country strings must match what GDACS/USGS put in
# location_metadata.country (usually English, from the feed).

_CONTINENT_COUNTRIES: Dict[str, set] = {
    "asia": {
        "afghanistan", "armenia", "azerbaijan", "bahrain", "bangladesh", "bhutan",
        "brunei", "cambodia", "china", "cyprus", "georgia", "india", "indonesia",
        "iran", "iraq", "israel", "japan", "jordan", "kazakhstan", "kuwait",
        "kyrgyzstan", "laos", "lebanon", "malaysia", "maldives", "mongolia",
        "myanmar", "nepal", "north korea", "oman", "pakistan", "palestine",
        "philippines", "qatar", "russia", "russian federation", "saudi arabia",
        "singapore", "south korea", "sri lanka", "syria", "taiwan", "tajikistan",
        "thailand", "timor-leste", "turkey", "turkmenistan", "uae",
        "united arab emirates", "uzbekistan", "vietnam", "yemen",
        "hong kong", "macau", "east timor", "republic of korea",
        "democratic people's republic of korea", "lao pdr",
    },
    "europe": {
        "albania", "andorra", "austria", "belarus", "belgium", "bosnia",
        "bosnia and herzegovina", "bulgaria", "croatia", "czech republic",
        "czechia", "denmark", "estonia", "finland", "france", "germany",
        "greece", "hungary", "iceland", "ireland", "italy", "kosovo", "latvia",
        "liechtenstein", "lithuania", "luxembourg", "malta", "moldova", "monaco",
        "montenegro", "netherlands", "north macedonia", "norway", "poland",
        "portugal", "romania", "russia", "russian federation", "san marino",
        "serbia", "slovakia", "slovenia", "spain", "sweden", "switzerland",
        "ukraine", "united kingdom", "uk", "england", "scotland", "wales",
        "britain", "great britain", "vatican", "turkey",
    },
    "africa": {
        "algeria", "angola", "benin", "botswana", "burkina faso", "burundi",
        "cabo verde", "cameroon", "central african republic", "chad", "comoros",
        "congo", "democratic republic of congo", "drc", "djibouti", "egypt",
        "equatorial guinea", "eritrea", "ethiopia", "gabon", "gambia", "ghana",
        "guinea", "guinea-bissau", "ivory coast", "cote d'ivoire", "côte d'ivoire",
        "kenya", "lesotho", "liberia", "libya", "madagascar", "malawi", "mali",
        "mauritania", "mauritius", "morocco", "mozambique", "namibia", "niger",
        "nigeria", "rwanda", "sao tome and principe", "senegal", "sierra leone",
        "somalia", "south africa", "south sudan", "sudan", "eswatini", "swaziland",
        "tanzania", "united republic of tanzania", "togo", "tunisia", "uganda",
        "zambia", "zimbabwe",
    },
    "north america": {
        "canada", "united states", "usa", "us", "mexico", "guatemala", "belize",
        "honduras", "el salvador", "nicaragua", "costa rica", "panama",
        "cuba", "haiti", "dominican republic", "jamaica", "puerto rico",
        "trinidad and tobago", "barbados", "grenada", "saint lucia", "bahamas",
        "antigua and barbuda", "dominica", "saint kitts and nevis",
        "saint vincent and the grenadines",
    },
    "south america": {
        "argentina", "bolivia", "brazil", "chile", "colombia", "ecuador",
        "guyana", "paraguay", "peru", "suriname", "uruguay", "venezuela",
        "french guiana",
    },
    "americas": {
        "canada", "united states", "usa", "us", "mexico", "guatemala", "belize",
        "honduras", "el salvador", "nicaragua", "costa rica", "panama",
        "cuba", "haiti", "dominican republic", "jamaica", "puerto rico",
        "trinidad and tobago", "barbados", "grenada", "saint lucia", "bahamas",
        "antigua and barbuda", "dominica", "saint kitts and nevis",
        "saint vincent and the grenadines",
        "argentina", "bolivia", "brazil", "chile", "colombia", "ecuador",
        "guyana", "paraguay", "peru", "suriname", "uruguay", "venezuela",
    },
    "oceania": {
        "australia", "new zealand", "fiji", "papua new guinea", "solomon islands",
        "vanuatu", "samoa", "tonga", "kiribati", "micronesia", "palau",
        "marshall islands", "nauru", "tuvalu",
    },
    "middle east": {
        "bahrain", "iran", "iraq", "israel", "jordan", "kuwait", "lebanon",
        "oman", "palestine", "qatar", "saudi arabia", "syria", "turkey",
        "uae", "united arab emirates", "yemen",
    },
    "southeast asia": {
        "brunei", "cambodia", "indonesia", "laos", "lao pdr", "malaysia",
        "myanmar", "philippines", "singapore", "thailand", "timor-leste",
        "vietnam", "east timor",
    },
    "south asia": {
        "afghanistan", "bangladesh", "bhutan", "india", "maldives",
        "nepal", "pakistan", "sri lanka",
    },
    "east asia": {
        "china", "hong kong", "japan", "macau", "mongolia",
        "north korea", "south korea", "taiwan",
    },
    "central asia": {
        "kazakhstan", "kyrgyzstan", "tajikistan", "turkmenistan", "uzbekistan",
    },
}


# ── Continent bounding boxes ─────────────────────────────────────────────────
# Used as a fallback for events that have no country name (e.g. NASA FIRMS).
# Format: (lat_min, lat_max, lon_min, lon_max)
_CONTINENT_BOUNDS: Dict[str, tuple] = {
    "asia":          (-12,  82,  25, 180),
    "europe":        ( 35,  72, -25,  45),
    "africa":        (-35,  38, -18,  52),
    "north america": ( 15,  84, -170, -52),
    "south america": (-56,  15,  -82, -34),
    "americas":      (-56,  84, -170, -34),
    "oceania":       (-48,   0,  110, 180),
    "middle east":   ( 12,  43,  25,  65),
    "southeast asia":(-12,  28,  95, 145),
    "south asia":    (  5,  37,  60,  93),
    "east asia":     ( 20,  54,  73, 145),
    "central asia":  ( 35,  56,  50,  90),
}


def _geo_filter_events(
    events: List[DisasterEvent],
    geographic_filter: Optional[str],
) -> List[DisasterEvent]:
    """
    Return only the events whose country belongs to the requested continent/region.

    For events with no country name (e.g. NASA FIRMS wildfire pixels), falls back
    to a lat/lon bounding box check so FIRMS hotspots still appear correctly on
    region-filtered maps.

    If geographic_filter is None, a specific country (already filtered by the
    tool), or an unrecognised region, the original list is returned unchanged.
    """
    if not geographic_filter or not events:
        return events

    key     = geographic_filter.lower().strip()
    allowed = _CONTINENT_COUNTRIES.get(key)
    if not allowed:
        return events   # specific country — tool already filtered

    bounds = _CONTINENT_BOUNDS.get(key)  # may be None for some entries

    filtered: List[DisasterEvent] = []
    for e in events:
        country = (e.location_metadata.country or "").lower().strip() if e.location_metadata else ""

        if country and country in allowed:
            filtered.append(e)
            continue

        # No country name — try coordinate bounding box (handles FIRMS data)
        if not country and bounds and e.location:
            coords = getattr(e.location, "coordinates", None)
            if coords and len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
                lat_min, lat_max, lon_min, lon_max = bounds
                if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                    filtered.append(e)

    # Safety-net: if everything was filtered out, return unfiltered
    if not filtered:
        logger.warning(
            "_geo_filter_events: all %d events excluded for %r — returning unfiltered",
            len(events), geographic_filter,
        )
        return events

    logger.info(
        "_geo_filter_events: %r → %d/%d events kept",
        geographic_filter, len(filtered), len(events),
    )
    return filtered


SAFETY_CRITICAL_PATTERN = re.compile(
    r"\b(evacuat(e|ion)|safe route|where should i go|shelter|is it safe)\b",
    re.IGNORECASE,
)

# Characters that should never appear in a legitimate disaster query
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_MAX_QUERY_LENGTH = 600


def _sanitize_query(query: str) -> str:
    """Strip control characters and cap length. Preserves Unicode (multilingual support)."""
    cleaned = _CONTROL_CHAR_RE.sub("", query)
    return cleaned[:_MAX_QUERY_LENGTH].strip()


class RouterDecision(BaseModel):
    route_target: Literal["live_tools", "historical_rag", "hybrid", "clarification_needed"]
    reason: str
    timeframe: str = Field(default="recent")
    location: Optional[str] = Field(default=None)
    intent: Literal["disaster_query", "general_chat"] = Field(default="disaster_query")
    geographic_filter: Optional[str] = Field(default=None)
    disaster_type: Optional[str] = Field(
        default=None,
        description=(
            "Specific disaster type if user asked about exactly ONE type. "
            "One of: 'flood', 'earthquake', 'cyclone', 'wildfire', 'tsunami', "
            "'volcano', 'drought'. Leave None when user asked about multiple or all types."
        ),
    )
    disaster_types: List[str] = Field(
        default_factory=list,
        description=(
            "When user asks about 2+ specific types simultaneously, list them ALL here. "
            "E.g. 'earthquakes and cyclones' → ['earthquake', 'cyclone']. "
            "'floods and wildfires in Asia' → ['flood', 'wildfire']. "
            "Leave empty when user asks about ALL types (no restriction) or exactly one type "
            "(use disaster_type for that). Never duplicate what is in disaster_type."
        ),
    )


# ── Multi-LLM: Groq → Gemini fallback ───────────────────────────────────────
# Both clients are built lazily (first call) so missing API keys don't crash
# startup.  If Groq hits a rate-limit or daily quota, we transparently retry
# the same prompt on Gemini.  If neither key is set the call raises a clear
# RuntimeError immediately.

@lru_cache(maxsize=1)
def _get_groq_llm():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        logger.warning("GROQ_API_KEY not set — Groq LLM unavailable")
        return None
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)


@lru_cache(maxsize=1)
def _get_gemini_llm():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            google_api_key=key,
        )
    except ImportError:
        logger.warning("langchain_google_genai not installed — Gemini unavailable")
        return None


def _is_rate_limit_error(err_str: str) -> bool:
    """Return True for any quota / rate-limit error that warrants an LLM switch."""
    lowered = err_str.lower()
    return (
        "rate_limit" in lowered
        or "429" in err_str
        or "tokens per day" in lowered
        or "tpd" in lowered
        or "quota" in lowered
        or "resource_exhausted" in lowered   # Gemini quota code
        or "overloaded" in lowered
    )


class _BothProvidersExhausted(RuntimeError):
    """Raised when every configured LLM provider is rate-limited / quota-exhausted."""


def _invoke_with_fallback(prompt: str) -> str:
    """Invoke Groq; fall back to Gemini on rate-limit / quota errors.

    If both providers are exhausted, raises ``_BothProvidersExhausted`` so
    callers can return a user-friendly message instead of a raw 500.
    """
    groq = _get_groq_llm()
    if groq is not None:
        try:
            return str(groq.invoke(prompt).content)
        except Exception as exc:
            if _is_rate_limit_error(str(exc)):
                logger.warning("Groq rate-limited (%s) — falling back to Gemini", exc)
            else:
                raise

    gemini = _get_gemini_llm()
    if gemini is not None:
        try:
            return str(gemini.invoke(prompt).content)
        except Exception as exc:
            if _is_rate_limit_error(str(exc)):
                logger.warning("Gemini also rate-limited (%s) — both providers exhausted", exc)
                raise _BothProvidersExhausted("Both Groq and Gemini are rate-limited.") from exc
            raise

    raise _BothProvidersExhausted(
        "No LLM available — set GROQ_API_KEY and/or GEMINI_API_KEY in your environment."
    )


def _invoke_structured_with_fallback(prompt: str) -> RouterDecision:
    """Invoke Groq structured output; fall back to Gemini on quota errors."""
    groq = _get_groq_llm()
    if groq is not None:
        try:
            result = groq.with_structured_output(RouterDecision).invoke(prompt)
            return result  # type: ignore[return-value]
        except Exception as exc:
            if _is_rate_limit_error(str(exc)):
                logger.warning(
                    "Groq rate-limited (structured) (%s) — falling back to Gemini", exc
                )
            else:
                raise

    gemini = _get_gemini_llm()
    if gemini is not None:
        try:
            result = gemini.with_structured_output(RouterDecision).invoke(prompt)
            return result  # type: ignore[return-value]
        except Exception as exc:
            if _is_rate_limit_error(str(exc)):
                logger.warning(
                    "Gemini also rate-limited (structured) (%s) — both providers exhausted", exc
                )
                raise _BothProvidersExhausted(
                    "Both Groq and Gemini are rate-limited."
                ) from exc
            raise

    raise _BothProvidersExhausted(
        "No LLM available — set GROQ_API_KEY and/or GEMINI_API_KEY in your environment."
    )


# ── Nodes ────────────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> Dict[str, Any]:
    query = _sanitize_query(state.user_query)

    if not query:
        return {
            "route_target": "clarification_needed",
            "route_reasoning": "Empty query.",
            "warnings": state.warnings + ["User query was empty."],
        }

    # Build recent conversation context (last 6 messages max — keeps token cost low)
    history_lines = ""
    if state.conversation_history:
        recent = state.conversation_history[-6:]
        history_lines = "\n".join(
            f"  [{m['role'].upper()}]: {m['content'][:200]}"
            for m in recent
        )
        history_lines = f"\nRecent conversation:\n{history_lines}\n"

    prompt = (
        "You are a routing controller for a disaster intelligence agent.\n"
        "The user may write in ANY language. Understand their intent regardless of language.\n\n"

        "── INTENT ──────────────────────────────────────────────────────────────\n"
        "First decide intent:\n"
        "- 'general_chat'   : greetings ('hello', 'hi'), thanks, questions about the current\n"
        "  date/time, questions about what the app does, small talk, anything that is NOT\n"
        "  about natural disasters. When intent is general_chat set route_target to\n"
        "  'clarification_needed' (the general_chat handler takes over).\n"
        "- 'disaster_query' : anything about earthquakes, floods, cyclones, wildfires,\n"
        "  tsunamis, droughts, volcanoes, or any natural disaster event.\n\n"

        "── ROUTING (only for disaster_query) ──────────────────────────────────\n"
        "Choose exactly one route_target:\n"
        "- live_tools      : event within the past 30 days\n"
        "  (e.g. 'today', 'this week', 'past 2 weeks', 'recent', 'latest', 'now').\n"
        "- historical_rag  : event explicitly MORE than 30 days ago\n"
        "  (e.g. 'last year', '2022', '6 months ago', 'since 2020').\n"
        "- hybrid          : 'when was the last X', 'most recent ever', 'has X ever happened'\n"
        "  — timeframe unknown, need both live and historical data.\n"
        "- clarification_needed : ONLY when intent is general_chat. NEVER use this for\n"
        "  disaster queries, even broad ones like 'all disasters worldwide' or\n"
        "  'what happened globally this week'.\n\n"

        "IMPORTANT: 'past N days/weeks' ≤ 30 → live_tools.\n"
        "IMPORTANT: 'when was the last / most recent / ever' → hybrid.\n"
        "IMPORTANT: Specific calendar date within last 30 days → live_tools.\n"
        "IMPORTANT: Specific calendar date older than 30 days → historical_rag.\n"
        "IMPORTANT: Broad queries ('all disasters', 'everything globally', 'what happened\n"
        "  in the world') → live_tools. NEVER mark these as clarification_needed.\n\n"

        "── EXTRACTION ──────────────────────────────────────────────────────────\n"
        "- timeframe: reproduce exact date if given (e.g. '01.05.2026'); otherwise\n"
        "  plain-English ('2 weeks', 'recent', '1 year'). Use 'recent' for general_chat.\n"
        "- location: specific country or city in English, if mentioned.\n"
        "- geographic_filter: broadest geographic scope mentioned.\n"
        "- disaster_type: ONLY set when the user asks about exactly ONE specific disaster\n"
        "  type. Use: 'flood', 'earthquake', 'cyclone', 'wildfire', 'tsunami',\n"
        "  'volcano', 'drought'. Leave null when the user asks about multiple/all types,\n"
        "  or uses words like 'disasters', 'events', 'natural disasters'.\n"
        "  Examples: 'floods in Asia' → 'flood'. 'earthquakes today' → 'earthquake'.\n"
        "  'any disasters this week' → null. 'what happened globally' → null.\n"
        "Always translate location names to English.\n"
        f"{history_lines}\n"
        f"User query: {query}"
    )
    try:
        decision = _invoke_structured_with_fallback(prompt)
    except _BothProvidersExhausted:
        return {
            "route_target": "clarification_needed",
            "synthesis_summary": (
                "Both AI providers have reached their quota limits for now. "
                "Groq resets at midnight UTC; please try again in a little while."
            ),
        }
    except Exception as exc:
        err_str = str(exc)
        logger.error("Router LLM failed: %s", err_str)
        if _is_rate_limit_error(err_str):
            return {
                "route_target": "clarification_needed",
                "synthesis_summary": (
                    "The AI service is temporarily rate-limited. "
                    "Please wait a moment and try again."
                ),
            }
        raise

    # ── Location resolution ──────────────────────────────────────────────────
    # `location` must be a specific country or city — it's used for per-event
    # string matching inside the tools. Continents, regions, and vague global
    # terms ("Asia", "globe", "world", "everywhere") are NOT valid country names
    # and will filter out ALL events. Only pass `location` when the router
    # extracted a specific country/city; use `geographic_filter` for the synthesis
    # geo-scope instruction only.
    _BROAD_SCOPES = {
        "asia", "europe", "africa", "americas", "north america", "south america",
        "oceania", "middle east", "southeast asia", "central asia", "east asia",
        "south asia", "pacific", "atlantic", "indian ocean", "arctic", "antarctic",
        "world", "worldwide", "globe", "global", "everywhere", "all over",
        "international", "earth", "planet", "western", "eastern", "northern", "southern",
    }

    def _is_specific_location(loc: str | None) -> bool:
        if not loc:
            return False
        return loc.lower().strip() not in _BROAD_SCOPES

    tool_location = decision.location if _is_specific_location(decision.location) else None

    # Normalise disaster_type: lowercase, strip, map synonyms
    _TYPE_SYNONYMS = {
        "floods": "flood", "flooding": "flood",
        "earthquakes": "earthquake", "quake": "earthquake", "seismic": "earthquake",
        "cyclones": "cyclone", "hurricane": "cyclone", "typhoon": "cyclone", "storm": "cyclone",
        "wildfires": "wildfire", "fire": "wildfire", "fires": "wildfire",
        "tsunamis": "tsunami",
        "volcanoes": "volcano", "volcanic": "volcano", "eruption": "volcano",
        "droughts": "drought",
    }
    _VALID_TYPES = {"flood", "earthquake", "cyclone", "wildfire", "tsunami", "volcano", "drought"}
    raw_type = (decision.disaster_type or "").lower().strip()
    raw_type = _TYPE_SYNONYMS.get(raw_type, raw_type)
    tool_disaster_type = raw_type if raw_type in _VALID_TYPES else None

    # Multi-type: normalise the list the LLM may have returned
    multi_types: List[str] = []
    for rt in (decision.disaster_types or []):
        rt_n = _TYPE_SYNONYMS.get(rt.lower().strip(), rt.lower().strip())
        if rt_n in _VALID_TYPES and rt_n not in multi_types:
            multi_types.append(rt_n)
    # If the LLM put the single type in disaster_types instead of disaster_type, merge it
    if tool_disaster_type and tool_disaster_type not in multi_types:
        if multi_types:                                    # only if there are already others
            multi_types.insert(0, tool_disaster_type)
    # A single-entry multi_types is the same as tool_disaster_type — collapse to avoid confusion
    if len(multi_types) == 1 and multi_types[0] == tool_disaster_type:
        multi_types = []

    tool_arguments = {
        "fetch_live_disasters": {
            "query":         query,
            "timeframe":     decision.timeframe or "recent",
            "location":      tool_location,
            "disaster_type": tool_disaster_type,
        },
        "search_historical_events": {
            "query":         query,
            "location":      tool_location,
            "timeframe":     decision.timeframe or "recent",
            "disaster_type": tool_disaster_type,
        },
    }
    selected_tools = (
        ["fetch_live_disasters"]
        if decision.route_target == "live_tools"
        else ["search_historical_events"]
        if decision.route_target == "historical_rag"
        else ["fetch_live_disasters", "search_historical_events"]
        if decision.route_target == "hybrid"
        else []
    )
    return {
        "route_target":             decision.route_target,
        "route_reasoning":          decision.reason,
        "selected_tools":           selected_tools,
        "tool_arguments":           tool_arguments,
        "intent":                   decision.intent,
        "geographic_filter":        decision.geographic_filter,
        "requested_disaster_type":  tool_disaster_type,
        "requested_disaster_types": multi_types,
    }


def live_tool_node(state: AgentState) -> Dict[str, Any]:
    args = state.tool_arguments.get("fetch_live_disasters", {})
    try:
        results = fetch_live_disasters.invoke(args)
        if not isinstance(results, list):
            results = [results]

        events = []
        for r in results:
            try:
                events.append(DisasterEvent.model_validate(r))
            except Exception:
                pass

        updated_results = dict(state.tool_results)
        updated_results["fetch_live_disasters"] = results
        return {
            "tool_results": updated_results,
            "normalized_events": state.normalized_events + events,
        }
    except Exception as exc:
        return {"tool_errors": state.tool_errors + [f"live tool failed: {exc}"]}


def historical_tool_node(state: AgentState) -> Dict[str, Any]:
    args = state.tool_arguments.get("search_historical_events", {})
    try:
        results = search_historical_events.invoke(args)
        if not isinstance(results, list):
            results = [results] if results else []

        events: List[DisasterEvent] = []
        for r in results:
            try:
                events.append(DisasterEvent.model_validate(r))
            except Exception:
                pass

        updated_results = dict(state.tool_results)
        updated_results["search_historical_events"] = results
        return {
            "tool_results": updated_results,
            "normalized_events": state.normalized_events + events,
        }
    except Exception as exc:
        return {"tool_errors": state.tool_errors + [f"historical tool failed: {exc}"]}


def hybrid_tool_node(state: AgentState) -> Dict[str, Any]:
    live_update = live_tool_node(state)
    merged_state = state.model_copy(update=live_update)
    historical_update = historical_tool_node(merged_state)

    merged_results = dict(live_update.get("tool_results", {}))
    merged_results.update(historical_update.get("tool_results", {}))

    merged_events: List[DisasterEvent] = []
    merged_events.extend(live_update.get("normalized_events", []))
    seen_ids = {ev.event_id for ev in merged_events}
    merged_events.extend(
        e for e in historical_update.get("normalized_events", [])
        if e.event_id not in seen_ids
    )
    merged_errors = (
        list(live_update.get("tool_errors", []))
        + list(historical_update.get("tool_errors", []))
    )

    update: Dict[str, Any] = {
        "tool_results": merged_results,
        "normalized_events": merged_events,
    }
    if merged_errors:
        update["tool_errors"] = merged_errors
    return update


def general_chat_node(state: AgentState) -> Dict[str, Any]:
    from datetime import datetime, timezone as _tz
    now_utc = datetime.now(_tz.utc).strftime("%A, %d %B %Y — %H:%M UTC")

    prompt = (
        "You are a knowledgeable, warm, and conversational disaster intelligence assistant.\n"
        "LANGUAGE RULE: Respond in the same language the user wrote in.\n\n"
        f"Current date and time (UTC): {now_utc}\n"
        "Note: this application uses UTC for all timestamps and event data.\n\n"
        f"The user said: \"{state.user_query}\"\n\n"
        "Respond naturally and helpfully:\n"
        "- If they asked about the date or time → tell them exactly, mention the app uses UTC.\n"
        "- If it's a greeting or small talk → reply warmly in 1–2 sentences, mention you can\n"
        "  help them track live and historical natural disaster events worldwide.\n"
        "- If they asked what you can do → briefly describe: live monitoring of earthquakes,\n"
        "  floods, cyclones, wildfires and more via GDACS and USGS; historical event search;\n"
        "  multilingual queries; interactive world map.\n"
        "- For anything else general → answer it genuinely and helpfully.\n"
        "Keep it concise (2–3 sentences max), warm, and human. Never mention APIs or system names."
    )
    try:
        summary = _invoke_with_fallback(prompt)
    except _BothProvidersExhausted:
        summary = (
            "Both AI providers are at their quota limit right now — please try again shortly."
        )
    return {"synthesis_summary": _clean(summary)}


def _clean(text: str) -> str:
    """Replace literal escape sequences the model may emit with real whitespace."""
    return text.replace("\\n\\n", "\n\n").replace("\\n", "\n").strip()


# Alert priority for ranking (lower = more important)
_ALERT_PRIORITY = {"Red": 0, "Orange": 1, "Green": 2}

MAX_EVENTS_FOR_SYNTHESIS = 10   # hard cap — keeps prompt well under token limits
MAX_RELIEFWEB_FETCHES    = 3    # only enrich the top GDACS events


def _rank_events(events: List[DisasterEvent]) -> List[DisasterEvent]:
    """
    Sort by alert severity (Red > Orange > Green), then by magnitude/date descending.
    Ensures type diversity: non-earthquake events are always included when present,
    so that floods/cyclones/wildfires aren't drowned out by seismic data.
    Returns at most MAX_EVENTS_FOR_SYNTHESIS events.
    """
    def sort_key(e: DisasterEvent):
        alert    = (e.severity.label or "Green") if e.severity else "Green"
        priority = _ALERT_PRIORITY.get(alert, 2)
        mag      = -(e.severity.value or 0.0) if e.severity else 0.0   # negate = desc
        return (priority, mag)

    ranked = sorted(events, key=sort_key)

    # Separate earthquake vs all other disaster types
    non_eq = [e for e in ranked if e.event_type.value != "earthquake"]
    eq     = [e for e in ranked if e.event_type.value == "earthquake"]

    # Always include ALL non-earthquake events first (up to the cap), then fill
    # remaining slots with earthquakes. Reserve at least 4 slots for earthquakes
    # so that earthquake-specific queries still get meaningful coverage.
    max_non_eq = min(len(non_eq), max(0, MAX_EVENTS_FOR_SYNTHESIS - min(4, len(eq))))
    selected   = non_eq[:max_non_eq]
    eq_slots   = MAX_EVENTS_FOR_SYNTHESIS - len(selected)
    selected  += eq[:eq_slots]

    # Re-sort the final mix so the response is ordered by severity
    selected.sort(key=sort_key)
    return selected


def _slim_event(event: DisasterEvent) -> dict:
    """
    Compact event dict for the LLM prompt.
    Strips raw_payload, tags and full coordinates — keeps only what the analyst needs.
    Reduces per-event token cost from ~500 to ~80 tokens.
    """
    country = (event.location_metadata.country or "") if event.location_metadata else ""
    place   = (event.location_metadata.place_name or "") if event.location_metadata else ""
    date    = event.occurred_at.strftime("%Y-%m-%d") if event.occurred_at else ""
    sev     = event.severity or {}
    label   = getattr(sev, "label", None) or ""
    mag     = getattr(sev, "value", None)

    slim: dict = {
        "source":   event.source_system,
        "type":     event.event_type.value,
        "country":  country,
        "place":    place[:120],
        "date":     date,
        "severity": label,
        "summary":  (event.narrative_summary or "")[:200],
    }
    if mag is not None:
        slim["magnitude_Mw"] = round(float(mag), 1)
    return slim


def synthesis_node(state: AgentState) -> Dict[str, Any]:
    # ── Short-circuit: summary already written upstream ──────────────────────
    # router_node writes synthesis_summary directly when both LLM providers are
    # quota-exhausted.  Returning {} here preserves the existing value in state
    # and avoids firing another (guaranteed-to-fail) LLM call.
    if state.synthesis_summary:
        logger.info("synthesis_node: summary already set upstream — skipping LLM call")
        return {}

    guardrail_violations      = list(state.guardrail_violations)
    unavailable_data_reasons  = list(state.unavailable_data_reasons)

    # ── Safety guardrail ────────────────────────────────────────────────────
    if SAFETY_CRITICAL_PATTERN.search(state.user_query):
        guardrail_violations.append(
            "Safety-critical guidance request detected; refusing evacuation/safety instructions."
        )
        return {
            "guardrail_violations": guardrail_violations,
            "synthesis_summary": (
                "For your safety, I'm unable to provide evacuation routes or shelter guidance. "
                "Please contact your local emergency services or civil protection authority "
                "for life-safety instructions."
            ),
        }

    req_type  = state.requested_disaster_type   # e.g. "flood", "earthquake", or None
    geo_scope = state.geographic_filter or "globally"

    # ── No data path ─────────────────────────────────────────────────────────
    if not state.normalized_events:
        api_failed = bool(state.tool_errors)

        unavailable_data_reasons.append(
            "Data feeds temporarily unavailable." if api_failed
            else "No major events found in monitoring feeds for this query."
        )

        # Compact history for context (no token blowout)
        history_note = ""
        if state.conversation_history:
            recent = state.conversation_history[-4:]
            lines  = " | ".join(
                f"[{m['role'].upper()}]: {m['content'][:120]}" for m in recent
            )
            history_note = f"Conversation context: {lines}\n\n"

        if api_failed:
            situation_instructions = (
                "The monitoring systems experienced temporary connectivity issues.\n"
                "Write exactly 2 sentences:\n"
                "1. Acknowledge there was a temporary issue fetching live disaster data.\n"
                "2. Ask the user to retry in a moment.\n"
                "Do NOT speculate about whether events occurred."
            )
        elif req_type:
            # User asked about a SPECIFIC type — give a direct, honest answer
            situation_instructions = (
                f"No significant {req_type} events were found in {geo_scope} for this "
                f"timeframe in global monitoring feeds.\n"
                "Write exactly 2 sentences:\n"
                f"1. State directly that no major {req_type}s were detected in "
                f"{geo_scope} during the relevant period.\n"
                "2. Briefly note that global feeds capture only significant events, so "
                "smaller or localised incidents may not appear.\n"
                "STRICT RULE: Do NOT list or mention any other disaster types. "
                "Do NOT name any specific agency, website, or organisation."
            )
        else:
            situation_instructions = (
                f"No high-impact events were found in {geo_scope} for this timeframe.\n"
                "Write exactly 2 sentences:\n"
                "1. State calmly that no major events were detected during this period.\n"
                "2. Note that global feeds capture only significant events.\n"
                "STRICT RULE: Do NOT name specific countries, agencies, or organisations "
                "the user did not mention."
            )

        no_data_prompt = (
            "You are a disaster intelligence analyst.\n"
            "LANGUAGE RULE: Respond in the EXACT SAME language as the user's query. "
            "If the user wrote in Marathi → reply in Marathi. Hindi → Hindi. "
            "English → English. Place names stay in English.\n\n"
            f"User query: \"{state.user_query}\"\n\n"
            f"{history_note}"
            f"{situation_instructions}\n\n"
            "Output only the 2 sentences — no headers, no bullets, no extra commentary."
        )
        try:
            summary = _invoke_with_fallback(no_data_prompt)
        except _BothProvidersExhausted:
            summary = (
                "Both AI providers have hit their quota limits right now. "
                "Groq resets at midnight UTC — please try again then."
            )
        return {
            "unavailable_data_reasons": unavailable_data_reasons,
            "synthesis_summary": _clean(summary),
        }

    # ── Geographic pre-filter ────────────────────────────────────────────────
    # When the user asked about a continent/region (e.g. "Asia"), the tool
    # fetched events globally because tool_location was None for broad scopes.
    # Filter down to only the countries that belong to the requested region
    # BEFORE ranking — this keeps synthesis focused and trims map pins to the
    # correct geography.
    geo_events = _geo_filter_events(state.normalized_events, state.geographic_filter)

    # ── Disaster type pre-filter for map ─────────────────────────────────────
    # For single-type queries the tool already filtered, so normalized_events
    # only contains the right type.  For multi-type queries (e.g. "earthquakes
    # AND cyclones") the tool fetches everything (disaster_type=None) so we
    # must filter here to stop unrelated types (floods, wildfires, …) from
    # appearing on the map or in the synthesis context.
    req_types: set = set()
    if state.requested_disaster_types:          # multi-type: ["earthquake","cyclone"]
        req_types = set(state.requested_disaster_types)
    elif state.requested_disaster_type:         # single-type already tool-filtered, but be safe
        req_types = {state.requested_disaster_type}

    if req_types:
        type_filtered = [e for e in geo_events if e.event_type.value in req_types]
        if type_filtered:                       # safety-net: don't blank if nothing matches
            logger.info(
                "synthesis: type-filter %d → %d events for %r",
                len(geo_events), len(type_filtered), req_types,
            )
            geo_events = type_filtered
        else:
            logger.warning(
                "synthesis: type-filter would remove ALL events for %r — keeping unfiltered",
                req_types,
            )

    # ── Rank and cap events ──────────────────────────────────────────────────
    selected = _rank_events(geo_events)
    logger.info(
        "synthesis: %d raw → %d after geo-filter → %d selected for synthesis",
        len(state.normalized_events), len(geo_events), len(selected),
    )

    # ── Build minimal context (token-safe) ───────────────────────────────────
    context_items: List[dict] = []
    reliefweb_count = 0

    for event in selected:
        context_items.append(_slim_event(event))

        # Enrich top GDACS events with humanitarian narrative (capped)
        if event.source_system == "GDACS" and reliefweb_count < MAX_RELIEFWEB_FETCHES:
            country = (event.location_metadata.country or "") if event.location_metadata else ""
            if country:
                try:
                    hw = fetch_humanitarian_context.invoke({
                        "disaster_type": event.event_type.value,
                        "country_name":  country,
                    })
                    if hw:
                        context_items.append({"humanitarian_context": hw[:400]})
                except Exception:
                    pass
            reliefweb_count += 1

    # ── Disaster type coverage summary ──────────────────────────────────────
    ALL_TYPES     = {"earthquake", "flood", "cyclone", "tsunami", "volcano", "drought", "wildfire"}
    present_types = {e.event_type.value for e in geo_events}
    absent_types  = ALL_TYPES - present_types

    # ── Type-specific rule ───────────────────────────────────────────────────
    # When user asked about ONE type, only show that type. Do NOT list irrelevant types.
    if req_type:
        type_rule = (
            f"REQUESTED TYPE: The user asked specifically about {req_type}s.\n"
            f"- ONLY describe {req_type} events from the data. Do NOT mention or list any\n"
            f"  other disaster types (earthquakes, floods, cyclones, etc.) that appear in the data.\n"
            f"- If the data contains {req_type} events → report them normally.\n"
            f"- If NO {req_type} events are in the data → state this directly in one sentence\n"
            f"  and do not list other types.\n"
        )
    else:
        type_rule = (
            f"Disaster types present in data: {', '.join(sorted(present_types)) or 'none'}.\n"
            f"Disaster types with NO events: {', '.join(sorted(absent_types)) or 'none'}.\n"
            "If the user asked broadly (all disasters / what happened), briefly note absent\n"
            "types once in a natural closing sentence.\n"
        )

    # ── Geo scope instruction ────────────────────────────────────────────────
    geo_clause = ""
    if state.geographic_filter:
        geo_clause = (
            f"SCOPE: The user asked specifically about {state.geographic_filter}. "
            "If data contains events outside this scope, exclude them silently.\n\n"
        )

    # Conversation history context — last 6 turns
    history_context = ""
    if state.conversation_history:
        recent = state.conversation_history[-6:]
        lines = "\n".join(
            f"  [{m['role'].upper()}]: {m['content'][:300]}"
            for m in recent
        )
        history_context = f"Previous conversation (for context only):\n{lines}\n\n"

    prompt = (
        "You are a disaster intelligence analyst who writes with the clarity of a good journalist\n"
        "and the warmth of a knowledgeable friend — never robotic, never bureaucratic.\n\n"
        "LANGUAGE RULE: Respond in the same language the user used. Place names stay in English.\n\n"
        f"{geo_clause}"
        f"{history_context}"
        f"{type_rule}\n"
        "WRITING RULES:\n"
        "1. Use ONLY the event data provided. Never invent figures, casualties, or places.\n"
        "2. Never give evacuation routes or life-safety instructions.\n"
        "3. Skip humanitarian context if unavailable — don't mention it.\n"
        "4. Write in flowing, natural prose. Avoid robotic 'Type:/Location:/Severity:' labels.\n"
        "5. Head each distinct event with ### [Disaster type] — [Country].\n"
        "6. Under each heading write 2–4 sentences covering what happened, where, when,\n"
        "   how strong, and any known impact — in a natural, readable way.\n"
        "7. Group events of the same type in the same country under one heading.\n"
        "8. Close with a single plain-English summary sentence across all events.\n"
        "9. No meta-commentary, no 'Note:' sections, no apologies.\n"
        "10. If the user follows up on a prior message, acknowledge context naturally.\n"
        "11. Where relevant, note global feeds capture significant events only — say it once,\n"
        "    naturally, not as a disclaimer block.\n\n"
        f"User query: {state.user_query}\n\n"
        f"Event data ({len(selected)} of {len(geo_events)} total):\n"
        f"{json.dumps(context_items, indent=None)}"
    )

    try:
        summary = _invoke_with_fallback(prompt)
    except _BothProvidersExhausted:
        return {
            "synthesis_summary": (
                "Both AI providers (Groq and Gemini) have hit their quota limits right now. "
                "Groq resets at midnight UTC — please try again then, "
                "or narrow your search to a specific country or event type in the meantime."
            )
        }
    except Exception as exc:
        err_str = str(exc)
        logger.error("LLM synthesis failed: %s", err_str)

        # Any rate-limit / quota / resource-exhausted error from either provider
        if _is_rate_limit_error(err_str):
            return {
                "synthesis_summary": (
                    "The AI processing limit has been reached for now. "
                    "This resets at midnight UTC — please try again then, "
                    "or narrow your search to a specific country or event type."
                )
            }

        # Payload-too-large
        if "413" in err_str or "too large" in err_str.lower():
            return {
                "synthesis_summary": (
                    "The query matched too many events to process right now. "
                    "Try narrowing your search — for example, specify a country or a shorter "
                    "time window such as 'earthquakes in Japan today'."
                )
            }
        raise

    return {
        "synthesis_summary": _clean(summary),
        "normalized_events": geo_events,   # map pins limited to requested region
    }
