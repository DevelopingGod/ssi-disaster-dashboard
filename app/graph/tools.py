import csv
import concurrent.futures
import email.utils
import httpx
import io
import logging
import os
import re
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool
from app.models.disaster import DisasterEvent

logger = logging.getLogger(__name__)

# ── Shared HTTP client ───────────────────────────────────────────────────────
_sync_client = httpx.Client(
    timeout=20.0,
    headers={"User-Agent": "Natural-Disaster.io/1.0 (academic-research)"},
    follow_redirects=True,
)


def _retry_get(url: str, *, retries: int = 2, backoff: float = 1.5, **kwargs) -> httpx.Response:
    """
    GET with automatic retry on transient failures.
    Sleeps `backoff` seconds between attempts. Raises on final failure.

    4xx errors are NOT retried — they are permanent client errors (wrong URL,
    auth required, forbidden, etc.) that will never succeed on retry.
    Only network errors and 5xx server errors are retried.
    """
    last_exc: Exception = RuntimeError(f"No attempts made for {url}")
    for attempt in range(retries):
        try:
            resp = _sync_client.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                # Client error — retrying won't change the outcome. Raise immediately.
                raise
            last_exc = exc
            logger.warning(
                "HTTP attempt %d/%d failed [%s]: %s",
                attempt + 1, retries, url, exc,
            )
            if attempt < retries - 1:
                time.sleep(backoff)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "HTTP attempt %d/%d failed [%s]: %s",
                attempt + 1, retries, url, exc,
            )
            if attempt < retries - 1:
                time.sleep(backoff)
    raise last_exc

# ── TTL cache ────────────────────────────────────────────────────────────────
class _TTLCache:
    """Lightweight in-process TTL cache — thread-safe via a lock."""
    def __init__(self, ttl_seconds: int) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry and (time.monotonic() - entry[1]) < self._ttl:
                return entry[0]
            self._store.pop(key, None)
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic())

_gdacs_cache      = _TTLCache(ttl_seconds=600)    # 10 min — GDACS updates ~every few hours
_gdacs_list_cache = _TTLCache(ttl_seconds=600)    # 10 min — EventList API
_usgs_cache       = _TTLCache(ttl_seconds=600)    # 10 min
_reliefweb_cache  = _TTLCache(ttl_seconds=1800)   # 30 min
_firms_cache      = _TTLCache(ttl_seconds=600)    # 10 min — FIRMS updates every ~3 h

_RELIEFWEB_HEADERS = {
    "User-Agent": "Natural-Disaster.io/1.0 (academic-research)",
    "Accept": "application/json",
}

# ── US State abbreviations → "United States" ────────────────────────────────
_US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC","PR","GU","AS","VI","MP",
    "Alaska","Hawaii","California","Nevada","Oregon","Washington","Montana",
    "Idaho","Wyoming","Colorado","Utah","Arizona","New Mexico","Texas",
    "Oklahoma","Kansas","Nebraska","South Dakota","North Dakota","Minnesota",
    "Iowa","Missouri","Arkansas","Louisiana","Wisconsin","Michigan","Illinois",
    "Indiana","Ohio","Kentucky","Tennessee","Mississippi","Alabama","Georgia",
    "Florida","South Carolina","North Carolina","Virginia","West Virginia",
    "Maryland","Delaware","Pennsylvania","New Jersey","New York",
    "Connecticut","Rhode Island","Massachusetts","Vermont","New Hampshire","Maine",
}

# ── Country alias table ──────────────────────────────────────────────────────
_COUNTRY_ALIASES: Dict[str, List[str]] = {
    "russia":        ["russian federation", "rf"],
    "south korea":   ["republic of korea", "korea, south"],
    "north korea":   ["dprk", "korea, north", "democratic people's republic of korea"],
    "united states": ["usa", "us", "america", "united states of america"],
    "uk":            ["united kingdom", "great britain", "england", "britain"],
    "iran":          ["islamic republic of iran"],
    "syria":         ["syrian arab republic"],
    "tanzania":      ["united republic of tanzania"],
    "vietnam":       ["viet nam"],
    "laos":          ["lao pdr", "lao people's democratic republic"],
    "taiwan":        ["chinese taipei", "republic of china"],
    "ivory coast":   ["cote d'ivoire", "côte d'ivoire"],
    "moldova":       ["republic of moldova"],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def map_gdacs_type(event_type: str) -> str:
    return {
        "EQ": "earthquake", "FL": "flood",  "TC": "cyclone",
        "TS": "tsunami",    "VO": "volcano", "DR": "drought",
        "WF": "wildfire",
    }.get(event_type.upper(), "other")


def _clean_gdacs_description(desc: str) -> str:
    """
    Strip sentences that contain GDACS's '[unknown]' placeholder text.

    GDACS RSS descriptions use templates like:
      "The cyclone affects these countries: [unknown] (vulnerability [unknown])."
    When country / vulnerability data is unavailable the literal token '[unknown]'
    is left in the string.  This looks unprofessional in the UI; we drop any
    sentence that contains the token and fall back to the event title if the
    entire description is cleaned away.
    """
    if "[unknown]" not in desc:
        return desc
    # Split on sentence boundaries (period / exclamation / question followed by whitespace)
    sentences = re.split(r"(?<=[.!?])\s+", desc)
    clean = [s for s in sentences if "[unknown]" not in s]
    return " ".join(clean).strip()


def _parse_rfc2822_date(date_str: str) -> Optional[datetime]:
    """
    Parse RSS (RFC 2822) and ISO 8601 date strings robustly.

    Handles all of the following correctly:
      RFC 2822 : "Wed, 15 Apr 2026 12:30:45 +0000"
      ISO full  : "2026-04-15T12:30:45.000Z"   (milliseconds + Z)
      ISO nosec : "2026-05-01T00:00Z"           (no seconds + Z)
      ISO plain : "2026-04-15T12:30:45"         (no timezone suffix)
      Date-only : "2026-05-01"
    """
    if not date_str:
        return None

    # ── Step 1: RFC 2822 (GDACS RSS feed uses this format) ──────────────────
    try:
        ts = email.utils.parsedate_to_datetime(date_str)
        return ts.astimezone(timezone.utc)
    except Exception:
        pass

    # ── Step 2: ISO 8601 normalisation ──────────────────────────────────────
    # Strip timezone suffix so strptime can parse the timestamp part cleanly:
    #   Z              → remove
    #   +HH:MM/-HH:MM  → remove
    #   +HHMM/-HHMM    → remove
    #   " GMT"/" UTC"  → remove (space-separated suffix)
    s = date_str.strip()
    s = re.sub(r'(Z|[+-]\d{2}:?\d{2})$', '', s)   # Z / ±HH:MM / ±HHMM
    s = re.sub(r'\s+(GMT|UTC)$', '', s)            # trailing "GMT" / "UTC"

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",   # 2026-04-15T12:30:45.123456
        "%Y-%m-%dT%H:%M:%S",      # 2026-04-15T12:30:45
        "%Y-%m-%dT%H:%M",         # 2026-05-01T00:00
        "%a, %d %b %Y %H:%M:%S",  # RFC 2822 without zone (last-ditch fallback)
        "%Y-%m-%d",               # 2026-05-01
    ):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.debug("_parse_rfc2822_date: unrecognised format %r", date_str)
    return None


def _cutoff_from_timeframe(timeframe: str) -> Optional[datetime]:
    """Convert a text timeframe to a UTC cutoff datetime."""
    t = timeframe.lower().strip()
    now = datetime.now(timezone.utc)

    # UTC midnight today — used for "today" / "yesterday" so we get the full calendar day,
    # not just the rolling last-N-hours window.
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if t in ("recent", "current", "live", "now", "latest"):
        return now - timedelta(days=30)
    if t == "today":
        return today_midnight                        # everything since 00:00 UTC today
    if t == "yesterday":
        return today_midnight - timedelta(days=1)   # everything since 00:00 UTC yesterday

    rolling_shortcuts = {
        "this week": 7, "past week": 7, "last week": 7,
        "this month": 30, "past month": 30, "last month": 30,
    }
    for key, days in rolling_shortcuts.items():
        if t == key:
            return now - timedelta(days=days)

    m = re.search(r"(\d+)\s*(day|week|month|year)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return now - {
            "day": timedelta(days=n),
            "week": timedelta(weeks=n),
            "month": timedelta(days=n * 30),
            "year": timedelta(days=n * 365),
        }[unit]

    # ── Try to parse a specific calendar date ───────────────────────────────
    # Handles: "01.05.2026", "2026-05-01", "May 1 2026", "1 May 2026", etc.
    raw = timeframe.strip()
    _date_formats = [
        "%d.%m.%Y",   # 01.05.2026
        "%d/%m/%Y",   # 01/05/2026
        "%m/%d/%Y",   # 05/01/2026
        "%Y-%m-%d",   # 2026-05-01
        "%B %d %Y",   # May 1 2026
        "%B %d, %Y",  # May 1, 2026
        "%d %B %Y",   # 1 May 2026
        "%b %d %Y",   # May 1 2026 (abbrev)
        "%b %d, %Y",  # May 1, 2026 (abbrev)
    ]
    for fmt in _date_formats:
        try:
            specific = datetime.strptime(raw, fmt).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
            )
            return specific   # cutoff = start of that day
        except ValueError:
            continue

    return now - timedelta(days=30)   # default


def _country_matches(feed_country: str, requested: str) -> bool:
    """Flexible country matching including aliases."""
    if not feed_country or not requested:
        return False
    f = feed_country.lower().strip()
    r = requested.lower().strip()
    if r == f or r in f or f in r:
        return True
    for canonical, aliases in _COUNTRY_ALIASES.items():
        if r == canonical or r in aliases:
            if f == canonical or any(a in f for a in aliases) or canonical in f:
                return True
    return False


def _extract_country_from_usgs_place(place: str) -> str:
    """
    Extract the country from a USGS place description.
    Examples:
      '75 km ENE of Hasaki, Japan'  → 'Japan'
      '24 km NE of Ute Park, New Mexico' → 'United States'
      'South Sandwich Islands region' → ''
    """
    if not place:
        return ""
    parts = [p.strip() for p in place.split(",")]
    if not parts:
        return ""
    last = parts[-1].strip()
    if last in _US_STATES:
        return "United States"
    if len(parts) >= 2:
        return last
    return ""


def _usgs_feed_url(timeframe: str) -> str:
    """Choose the right USGS M2.5+ feed based on timeframe."""
    t = timeframe.lower()
    if any(x in t for x in ("today", "24 hour", "1 day", "hour")):
        return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    if any(x in t for x in ("week", "7 day")):
        return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
    return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson"


def _fetch_usgs_earthquakes(
    timeframe: str = "recent",
    location: Optional[str] = None,
    cutoff: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Fetch M2.5+ earthquakes from USGS GeoJSON feed with location/date filtering."""
    url = _usgs_feed_url(timeframe)

    # ── Cache layer ──────────────────────────────────────────────────────────
    # IMPORTANT: only cache non-empty feature lists. An empty list cached here
    # would poison all subsequent requests within the TTL window.
    cached_features = _usgs_cache.get(url)
    if cached_features is not None:
        logger.debug("USGS cache hit: %s (%d features)", url, len(cached_features))
        features = cached_features
    else:
        try:
            resp = _retry_get(url, timeout=20.0)
            features = resp.json().get("features", [])
            if features:
                _usgs_cache.set(url, features)
                logger.info("USGS: cached %d features from %s", len(features), url)
            else:
                logger.warning("USGS returned 0 features from %s — skipping cache", url)
        except Exception as exc:
            logger.error("USGS fetch failed after retries: %s", exc)
            return []

    # Global queries: only M4.0+ to keep context manageable.
    # Location-specific queries: M2.5+ for completeness.
    min_mag = 2.5 if location else 4.0
    # Hard cap: never send more than this many events to synthesis
    max_results = 20 if location else 15

    events: List[Dict[str, Any]] = []
    for feature in features:
        if len(events) >= max_results:
            break
        try:
            props = feature.get("properties", {})
            geom  = feature.get("geometry", {})

            mag = props.get("mag")
            if mag is None or float(mag) < min_mag:
                continue

            place = props.get("place", "")
            time_ms = props.get("time", 0)
            usgs_id = feature.get("id", "")
            alert   = props.get("alert") or "green"
            title   = props.get("title", f"M{mag} earthquake")

            # Country
            country = _extract_country_from_usgs_place(place)

            # Location filter
            if location:
                if country:
                    if not _country_matches(country, location):
                        # Secondary: check raw place string
                        if location.lower() not in place.lower():
                            continue
                else:
                    if location.lower() not in place.lower():
                        continue

            # Coordinates [lon, lat, depth]
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = float(coords[0]), float(coords[1])

            # Timestamp
            event_dt = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
            if cutoff and event_dt < cutoff:
                continue

            alert_level = {
                "red": "Red", "orange": "Orange",
                "yellow": "Orange", "green": "Green",
            }.get(str(alert).lower(), "Green")

            event_dict = {
                "event_id":        f"usgs-{usgs_id}",
                "event_type":      "earthquake",
                "source_system":   "USGS",
                "source_event_id": usgs_id,
                "occurred_at":     event_dt.isoformat(),
                "location": {
                    "type":        "Point",
                    "coordinates": [lon, lat],
                },
                "location_metadata": {
                    "country":    country or place,
                    "place_name": title,
                },
                "severity": {
                    "value": float(mag) if mag is not None else None,
                    "unit":  "Mw",
                    "label": alert_level,
                },
                "narrative_summary": f"M{mag} earthquake — {place}",
                "tags": ["live", "usgs", "earthquake", alert_level.lower()],
                "raw_payload": props,
            }
            DisasterEvent.model_validate(event_dict)
            events.append(event_dict)

        except Exception as exc:
            logger.warning("Failed to parse USGS feature: %s", exc)
            continue

    logger.info("USGS: location=%r timeframe=%r → %d earthquakes", location, timeframe, len(events))
    return events


# ── GDACS EventList helper (all disaster types, date-filtered) ───────────────

def _fetch_gdacs_eventlist(
    from_dt: datetime,
    to_dt: Optional[datetime] = None,
    location: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query the GDACS EventList API for all disaster types within a date window.
    This supplements the RSS feed (which only shows currently *active* alerts)
    with events that started in the requested time range.
    """
    now   = datetime.now(timezone.utc)
    to_dt = to_dt or now

    cache_key = (
        f"gdacs_list:{from_dt.strftime('%Y%m%d')}:"
        f"{to_dt.strftime('%Y%m%d')}:{location or ''}"
    )
    cached = _gdacs_list_cache.get(cache_key)
    if cached is not None:
        logger.debug("GDACS EventList cache hit: %s (%d events)", cache_key, len(cached))
        return cached

    url    = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    params = {
        "eventlist":  "EQ,FL,TC,VO,WF,DR,TS",
        "fromDate":   from_dt.strftime("%Y-%m-%d"),
        "toDate":     to_dt.strftime("%Y-%m-%d"),
        "alertlevel": "Green,Orange,Red",
    }
    try:
        resp = _retry_get(url, params=params, timeout=20.0)
        features = resp.json().get("features", [])
    except Exception as exc:
        logger.warning("GDACS EventList fetch failed: %s", exc)
        return []

    events: List[Dict[str, Any]] = []
    for feature in features:
        try:
            props   = feature.get("properties", {})
            geom    = feature.get("geometry", {})
            country = props.get("country", "")

            if location and not _country_matches(country, location):
                continue

            event_type  = map_gdacs_type(props.get("eventtype", "OTHER"))
            event_id    = str(props.get("eventid", len(events)))
            alert_level = props.get("alertlevel", "Green")
            title       = props.get("name") or props.get("htmldescription") or f"{event_type} in {country}"

            event_dt    = None
            occurred_at = now.isoformat()
            for date_key in ("fromdate", "todate", "dateadded"):
                raw = props.get(date_key, "")
                if raw:
                    event_dt = _parse_rfc2822_date(raw)
                    if event_dt:
                        occurred_at = event_dt.isoformat()
                        break

            # Only include events that actually fall within the requested window
            if event_dt and event_dt < from_dt:
                continue

            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) < 2:
                    continue
                lon, lat = float(coords[0]), float(coords[1])
            else:
                bbox  = str(props.get("bbox", ""))
                parts = [float(x) for x in bbox.split(",") if x.strip()]
                if len(parts) == 4:
                    lon = (parts[0] + parts[2]) / 2
                    lat = (parts[1] + parts[3]) / 2
                else:
                    continue

            mag_value = props.get("magnitude") or props.get("severitydata", {}).get("magnitude")

            event_dict = {
                "event_id":        f"gdacs-{event_id}",
                "event_type":      event_type,
                "source_system":   "GDACS",
                "source_event_id": event_id,
                "occurred_at":     occurred_at,
                "location": {"type": "Point", "coordinates": [lon, lat]},
                "location_metadata": {"country": country, "place_name": title},
                "severity": {
                    "label": alert_level,
                    "value": float(mag_value) if mag_value else None,
                },
                "narrative_summary": f"{event_type.capitalize()} — {country}: {title}",
                "tags": ["live", "gdacs", alert_level.lower(), event_type],
                "raw_payload": {"title": title, "alert_level": alert_level},
            }
            DisasterEvent.model_validate(event_dict)
            events.append(event_dict)

            if len(events) >= 30:
                break

        except Exception as exc:
            logger.warning("GDACS EventList parse error: %s", exc)
            continue

    if events:
        _gdacs_list_cache.set(cache_key, events)
    logger.info(
        "GDACS EventList: from=%s to=%s location=%r → %d events",
        from_dt.date(), to_dt.date(), location, len(events),
    )
    return events


# ── NASA FIRMS wildfire helper ───────────────────────────────────────────────

# Ordered from most specific to broadest — first match wins.
# Each tuple: (lat_min, lat_max, lon_min, lon_max, country_or_region_label)
_FIRMS_REGION_BOXES: List[Tuple[float, float, float, float, str]] = [
    # North America
    ( 24,  49, -125,  -65, "United States"),
    ( 49,  72, -141,  -52, "Canada"),
    ( 14,  33, -118,  -85, "Mexico"),
    (  7,  18,  -92,  -77, "Central America"),
    ( 10,  24,  -85,  -60, "Caribbean"),
    # South America
    (-56, -17,  -76,  -52, "Argentina / Chile"),
    ( -5,  12,  -82,  -35, "Colombia / Venezuela"),
    (-34,  -5,  -74,  -35, "Brazil"),
    (-22, -10,  -75,  -57, "Bolivia / Peru"),
    # Europe
    ( 35,  72,  -10,   30, "Europe"),
    # Africa
    ( 15,  38,  -18,   60, "North Africa / Middle East"),
    (  5,  20,  -18,   25, "West Africa"),
    ( -5,  15,   25,   42, "Central Africa"),
    (-35,  -5,   12,   40, "Southern / East Africa"),
    # Middle East / Central Asia
    ( 20,  42,   30,   65, "Middle East / Central Asia"),
    # South Asia
    (  7,  37,   62,   97, "South Asia"),
    # Russia / Siberia — split east/west because lon wraps 180
    ( 50,  78,  130,  180, "Russia (Far East)"),
    ( 50,  78,   60,  130, "Russia (Siberia)"),
    ( 45,  70,   27,   60, "Russia (West)"),
    # East / Southeast Asia
    ( 18,  54,   97,  135, "China"),
    (  0,  23,   92,  141, "Southeast Asia"),
    ( 30,  47,  128,  146, "Japan / Korea"),
    # Oceania
    (-47, -10,  112,  154, "Australia"),
    (-48,  -5,  165,  180, "New Zealand / Pacific"),
]


def _latlon_to_region(lat: float, lon: float) -> str:
    """Best-effort country/region label from a WGS-84 lat/lon point.

    Uses a static ordered list of bounding boxes — first match wins.
    Accurate enough for wildfire country attribution without any external API.
    """
    for lat_min, lat_max, lon_min, lon_max, label in _FIRMS_REGION_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return label
    return ""


def _cutoff_to_firms_days(timeframe: str) -> int:
    """Convert a text timeframe to a FIRMS day_range (1–10)."""
    t = timeframe.lower()
    if "today" in t or "1 day" in t or "24" in t:
        return 1
    if "yesterday" in t or "2 day" in t:
        return 2
    if "week" in t or "7 day" in t:
        return 7
    return 2   # default: last 48 h


def _fetch_firms_wildfires(
    timeframe: str = "recent",
    location: Optional[str] = None,
    cutoff: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch active wildfire hotspots from NASA FIRMS (VIIRS SNPP Near Real-Time).

    Requires FIRMS_MAP_KEY in the environment — obtain a free key at
    https://firms.modaps.eosdis.nasa.gov/api/area/

    Raw pixel detections are 1°-grid-clustered and ranked by fire radiative
    power (FRP, MW) so only the most significant hotspots are returned.
    """
    firms_key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not firms_key:
        logger.debug("FIRMS_MAP_KEY not set — skipping NASA FIRMS wildfire data")
        return []

    day_range = min(_cutoff_to_firms_days(timeframe), 10)
    cache_key = f"firms:global:{day_range}"
    cached    = _firms_cache.get(cache_key)
    if cached is not None:
        logger.debug("FIRMS cache hit: %s (%d events)", cache_key, len(cached))
        return cached

    # The FIRMS area CSV endpoint rejects the full-world bounding box and the
    # "world" keyword.  Split into two hemispheres (both confirmed 200 OK) and
    # fetch in parallel — net latency ≈ one request, full global coverage.
    _HEMI = ["-180,-90,0,90", "0,-90,180,90"]

    def _fetch_hemi(bbox: str) -> str:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
            f"/{firms_key}/VIIRS_SNPP_NRT/{bbox}/{day_range}"
        )
        try:
            return _retry_get(url, timeout=30.0).text
        except Exception as exc:
            logger.warning("NASA FIRMS fetch failed (bbox=%s): %s", bbox, exc)
            return ""

    raw_csv_parts: List[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for text in pool.map(_fetch_hemi, _HEMI):
            if text:
                raw_csv_parts.append(text)

    # Merge: keep one header row, concatenate all data rows.
    header: Optional[str] = None
    data_lines: List[str] = []
    for part in raw_csv_parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        if header is None:
            header = lines[0]
            data_lines.extend(lines[1:])
        else:
            data_lines.extend(lines[1:])   # skip duplicate header

    if not header:
        logger.warning("NASA FIRMS: no data returned from either hemisphere")
        return []

    combined_csv = header + "\n" + "\n".join(data_lines)

    # ── Parse CSV and cluster into 1° grid cells ─────────────────────────────
    clusters: Dict[str, dict] = {}
    try:
        reader = csv.DictReader(io.StringIO(combined_csv))
        for row in reader:
            try:
                # "l" = low confidence → skip; "n" = nominal, "h" = high → keep
                if row.get("confidence", "l") == "l":
                    continue
                lat  = float(row["latitude"])
                lon  = float(row["longitude"])
                frp  = float(row.get("frp") or 0)
                date = row.get("acq_date", "")

                key = f"{round(lat)}:{round(lon)}"
                if key not in clusters:
                    clusters[key] = {"lat": lat, "lon": lon, "frp": frp, "date": date, "count": 1}
                else:
                    clusters[key]["count"] += 1
                    if frp > clusters[key]["frp"]:
                        clusters[key]["frp"]  = frp
                        clusters[key]["lat"]  = lat
                        clusters[key]["lon"]  = lon
                        clusters[key]["date"] = date
            except (ValueError, KeyError):
                continue
    except Exception as exc:
        logger.warning("FIRMS CSV parse failed: %s", exc)
        return []

    # ── Take top 15 hotspots by fire radiative power ──────────────────────────
    top = sorted(clusters.values(), key=lambda x: x["frp"], reverse=True)[:15]

    events: List[Dict[str, Any]] = []
    for idx, c in enumerate(top):
        try:
            event_dt = (
                datetime.strptime(c["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if c["date"] else datetime.now(timezone.utc)
            )
        except ValueError:
            event_dt = datetime.now(timezone.utc)

        # Date filter
        if cutoff and event_dt < cutoff:
            continue

        lat_label = f"{abs(c['lat']):.1f}{'N' if c['lat'] >= 0 else 'S'}"
        lon_label = f"{abs(c['lon']):.1f}{'E' if c['lon'] >= 0 else 'W'}"
        severity  = "Red" if c["frp"] > 100 else "Orange" if c["frp"] > 30 else "Green"
        region    = _latlon_to_region(c["lat"], c["lon"])

        event_dict = {
            "event_id":        f"firms-{idx}-{round(c['lat'])}-{round(c['lon'])}",
            "event_type":      "wildfire",
            "source_system":   "NASA FIRMS",
            "source_event_id": f"firms-{idx}",
            "occurred_at":     event_dt.isoformat(),
            "location":        {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
            "location_metadata": {
                "country":    region,
                "place_name": (
                    f"Active fire cluster at {lat_label}, {lon_label} "
                    f"({c['count']} detections, FRP {c['frp']:.0f} MW)"
                ),
            },
            "severity":  {"label": severity, "value": c["frp"], "unit": "MW"},
            "narrative_summary": (
                f"Active wildfire hotspot at {lat_label}, {lon_label} — "
                f"{c['count']} satellite detections, peak fire radiative power {c['frp']:.0f} MW"
            ),
            "tags":        ["live", "nasa-firms", "wildfire", severity.lower()],
            "raw_payload": {"frp": c["frp"], "pixel_count": c["count"]},
        }
        try:
            DisasterEvent.model_validate(event_dict)
            events.append(event_dict)
        except Exception as exc:
            logger.warning("FIRMS event validation: %s", exc)

    if events:
        _firms_cache.set(cache_key, events)
    logger.info(
        "NASA FIRMS: %d wildfire hotspots (day_range=%d, location=%r)",
        len(events), day_range, location,
    )
    return events


# ── Tool: fetch live disasters ───────────────────────────────────────────────

@tool
def fetch_live_disasters(
    query: str,
    timeframe: str = "recent",
    location: Optional[str] = None,
    disaster_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch recent disaster events from GDACS (all types) and USGS (earthquakes).
    Filters by country, date, and optionally disaster type at the data layer.
    When disaster_type is set to a non-earthquake type, USGS is skipped entirely.
    """
    cutoff = _cutoff_from_timeframe(timeframe)

    # ── GDACS RSS ────────────────────────────────────────────────────────────
    _GDACS_RSS_KEY = "gdacs_rss"
    gdacs_events: List[Dict[str, Any]] = []
    _gdacs_fetch_failed = False
    try:
        cached_xml = _gdacs_cache.get(_GDACS_RSS_KEY)
        if cached_xml is not None:
            logger.debug("GDACS cache hit (%d bytes)", len(cached_xml))
            rss_text = cached_xml
        else:
            resp = _retry_get("https://www.gdacs.org/xml/rss.xml", timeout=20.0)
            rss_text = resp.text
            # Only cache if the feed actually contains event items
            if "<item>" in rss_text:
                _gdacs_cache.set(_GDACS_RSS_KEY, rss_text)
                logger.info("GDACS: cached RSS (%d bytes)", len(rss_text))
            else:
                logger.warning("GDACS RSS contains no items — skipping cache")
        root = ET.fromstring(rss_text)
        ns = {
            "geo":    "http://www.w3.org/2003/01/geo/wgs84_pos#",
            "gdacs":  "http://www.gdacs.org",
            "georss": "http://www.georss.org/georss",
        }
        for item in root.findall(".//item"):
            try:
                title          = item.findtext("title", default="Unknown Event")
                description    = item.findtext("description", default="")
                event_type_raw = item.findtext("gdacs:eventtype", default="OTHER", namespaces=ns)
                event_type     = map_gdacs_type(event_type_raw)
                alert_level    = item.findtext("gdacs:alertlevel", default="Green", namespaces=ns)
                country        = item.findtext("gdacs:country", default="", namespaces=ns)
                event_id_raw   = item.findtext("gdacs:eventid", default="", namespaces=ns)

                # Country filter
                if location and not _country_matches(country, location):
                    continue

                # Coordinates — nested under geo:Point, fallback to georss:point
                lat = item.findtext(".//geo:lat", namespaces=ns)
                lon = item.findtext(".//geo:long", namespaces=ns)
                if not lat or not lon:
                    gp = item.findtext("georss:point", namespaces=ns)
                    if gp:
                        parts = gp.split()
                        if len(parts) == 2:
                            lat, lon = parts[0], parts[1]
                if not lat or not lon:
                    continue

                # Date
                event_dt    = _parse_rfc2822_date(
                    item.findtext("gdacs:fromdate", namespaces=ns) or ""
                )
                occurred_at = event_dt.isoformat() if event_dt else datetime.now(timezone.utc).isoformat()

                # Timeframe filter
                if cutoff and event_dt and event_dt < cutoff:
                    continue

                event_dict = {
                    "event_id":      f"gdacs-{event_id_raw or len(gdacs_events)}",
                    "event_type":    event_type,
                    "source_system": "GDACS",
                    "source_event_id": event_id_raw,
                    "occurred_at":   occurred_at,
                    "location": {
                        "type":        "Point",
                        "coordinates": [float(lon), float(lat)],
                    },
                    "location_metadata": {
                        "country":    country,
                        "place_name": title,
                    },
                    "severity":          {"label": alert_level},
                    "narrative_summary": _clean_gdacs_description(description) or title,
                    "tags": ["live", "gdacs", alert_level.lower(), event_type],
                    "raw_payload":   {"title": title, "alert_level": alert_level},
                }
                DisasterEvent.model_validate(event_dict)
                gdacs_events.append(event_dict)
            except Exception as exc:
                logger.warning("GDACS item parse error: %s", exc)
                continue
    except Exception as exc:
        logger.error("GDACS RSS fetch/parse failed: %s", exc)
        _gdacs_fetch_failed = True

    # ── Disaster type filter on GDACS RSS events ────────────────────────────
    if disaster_type and disaster_type != "all":
        gdacs_events = [e for e in gdacs_events if e.get("event_type") == disaster_type]

    # ── GDACS EventList — supplements RSS with all disaster types for the window
    # The RSS feed only carries *currently active* alerts; the EventList API
    # returns events that *started* within the requested date range.
    if cutoff:
        try:
            list_events = _fetch_gdacs_eventlist(from_dt=cutoff, location=location)
            # Apply type filter to EventList results too
            if disaster_type and disaster_type != "all":
                list_events = [e for e in list_events if e.get("event_type") == disaster_type]
            existing_ids = {e["event_id"] for e in gdacs_events}
            added = 0
            for ev in list_events:
                if ev["event_id"] not in existing_ids:
                    gdacs_events.append(ev)
                    existing_ids.add(ev["event_id"])
                    added += 1
            if added:
                logger.info("GDACS EventList added %d non-RSS events (type=%r)", added, disaster_type)
        except Exception as exc:
            logger.warning("GDACS EventList integration failed (non-fatal): %s", exc)

    # ── USGS Earthquakes ─────────────────────────────────────────────────────
    # Skip USGS entirely when user asked about a non-earthquake disaster type.
    # USGS only monitors seismic activity — returning earthquakes for a flood
    # query produces irrelevant, misleading results.
    skip_usgs = bool(disaster_type and disaster_type not in ("earthquake", "all"))
    if skip_usgs:
        usgs_events: List[Dict[str, Any]] = []
        logger.info("USGS skipped — query is type-specific: %r", disaster_type)
    else:
        usgs_events = _fetch_usgs_earthquakes(
            timeframe=timeframe,
            location=location,
            cutoff=cutoff,
        )

    # ── NASA FIRMS Wildfires ──────────────────────────────────────────────────
    # Skip FIRMS when the user asked about a non-wildfire type.
    # FIRMS only tracks active fire/thermal anomalies — including it for flood
    # or earthquake queries would add irrelevant markers.
    skip_firms = bool(disaster_type and disaster_type not in ("wildfire", "all"))
    if skip_firms:
        firms_events: List[Dict[str, Any]] = []
        logger.info("FIRMS skipped — query is type-specific: %r", disaster_type)
    else:
        firms_events = _fetch_firms_wildfires(
            timeframe=timeframe,
            location=location,
            cutoff=cutoff,
        )

    # Merge: start with GDACS + USGS, then append FIRMS (GDACS may already have
    # some wildfire events; firms- prefix ensures no id collision).
    all_events = gdacs_events + usgs_events
    existing_ids = {e["event_id"] for e in all_events}
    for ev in firms_events:
        if ev["event_id"] not in existing_ids:
            all_events.append(ev)
            existing_ids.add(ev["event_id"])
    logger.info(
        "fetch_live_disasters: gdacs=%d usgs=%d total=%d (location=%r timeframe=%r)",
        len(gdacs_events), len(usgs_events), len(all_events), location, timeframe,
    )

    # If every source failed with an actual exception AND we have zero events,
    # raise so the calling node can surface "data unavailable" instead of
    # silently reporting "no events found."
    if not all_events and _gdacs_fetch_failed and not usgs_events:
        raise RuntimeError(
            "Live monitoring feeds (GDACS + USGS) are temporarily unavailable. "
            "Please retry in a moment."
        )

    return all_events


# ── Tool: search historical events ──────────────────────────────────────────

@tool
def search_historical_events(
    query: str,
    location: Optional[str] = None,
    timeframe: Optional[str] = None,
    disaster_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search GDACS historical event database for past disasters."""
    now    = datetime.now(timezone.utc)
    from_dt = _cutoff_from_timeframe(timeframe) if timeframe else now - timedelta(days=365)

    # Build the GDACS eventlist filter — only request the relevant type if specified
    _GDACS_TYPE_MAP = {
        "earthquake": "EQ", "flood": "FL", "cyclone": "TC",
        "volcano": "VO", "wildfire": "WF", "drought": "DR", "tsunami": "TS",
    }
    if disaster_type and disaster_type in _GDACS_TYPE_MAP:
        event_list_param = _GDACS_TYPE_MAP[disaster_type]
    else:
        event_list_param = "EQ,FL,TC,VO,WF,DR,TS"

    url    = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    params = {
        "eventlist":  event_list_param,
        "fromDate":   from_dt.strftime("%Y-%m-%d"),
        "toDate":     now.strftime("%Y-%m-%d"),
        "alertlevel": "Green,Orange,Red",
    }
    try:
        resp = _retry_get(url, params=params, timeout=20.0)
        features = resp.json().get("features", [])
    except Exception as exc:
        logger.error("GDACS historical search failed after retries: %s", exc)
        return []

    events: List[Dict[str, Any]] = []
    for feature in features:
        try:
            props = feature.get("properties", {})
            geom  = feature.get("geometry", {})
            country = props.get("country", "")

            if location and not _country_matches(country, location):
                continue

            event_type  = map_gdacs_type(props.get("eventtype", "OTHER"))
            event_id    = str(props.get("eventid", len(events)))
            alert_level = props.get("alertlevel", "Green")
            title       = props.get("name") or props.get("htmldescription") or f"{event_type} in {country}"

            event_dt    = None
            occurred_at = now.isoformat()
            for date_key in ("fromdate", "todate", "dateadded"):
                raw = props.get(date_key, "")
                if raw:
                    event_dt = _parse_rfc2822_date(raw)
                    if event_dt:
                        occurred_at = event_dt.isoformat()
                        break

            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) < 2:
                    continue
                lon, lat = float(coords[0]), float(coords[1])
            else:
                bbox = str(props.get("bbox", ""))
                parts = [float(x) for x in bbox.split(",") if x.strip()]
                if len(parts) == 4:
                    lon = (parts[0] + parts[2]) / 2
                    lat = (parts[1] + parts[3]) / 2
                else:
                    continue

            event_dict = {
                "event_id":        f"gdacs-hist-{event_id}",
                "event_type":      event_type,
                "source_system":   "GDACS",
                "source_event_id": event_id,
                "occurred_at":     occurred_at,
                "location": {"type": "Point", "coordinates": [lon, lat]},
                "location_metadata": {"country": country, "place_name": title},
                "severity":          {"label": alert_level},
                "narrative_summary": f"{event_type.capitalize()} — {country}: {title}",
                "tags": ["historical", "gdacs", alert_level.lower(), event_type],
                "raw_payload":       props,
            }
            DisasterEvent.model_validate(event_dict)
            events.append(event_dict)
            if len(events) >= 15:
                break
        except Exception as exc:
            logger.warning("GDACS historical parse error: %s", exc)
            continue

    logger.info("search_historical_events: location=%r → %d events", location, len(events))
    return events


# ── Tool: fetch humanitarian context ────────────────────────────────────────

@tool
def fetch_humanitarian_context(disaster_type: str, country_name: str) -> str:
    """Fetch humanitarian narrative context from ReliefWeb."""
    parts = []
    if disaster_type and disaster_type != "other":
        parts.append(disaster_type)
    if country_name:
        parts.append(country_name)

    cache_key = f"reliefweb:{disaster_type}:{country_name}"
    cached_result = _reliefweb_cache.get(cache_key)
    if cached_result is not None:
        logger.debug("ReliefWeb cache hit: %s", cache_key)
        return cached_result

    encoded = urllib.parse.quote(" AND ".join(parts) if parts else "disaster")
    url = (
        f"https://api.reliefweb.int/v2/reports"
        f"?appname=IEEE-Disaster-Dashboard-S2I3"
        f"&query[value]={encoded}"
        f"&limit=1&sort[]=date:desc"
        f"&fields[include][]=title&fields[include][]=body&fields[include][]=url"
    )
    try:
        resp = _retry_get(url, headers=_RELIEFWEB_HEADERS, timeout=15.0)
        if resp.status_code != 200:
            logger.warning("ReliefWeb %s for %s/%s", resp.status_code, disaster_type, country_name)
            _reliefweb_cache.set(cache_key, "")   # cache the miss — don't hammer a dead endpoint
            return ""
        data = resp.json()
        if data.get("data"):
            fields = data["data"][0].get("fields", {})
            title  = fields.get("title", "")
            body   = fields.get("body", "")
            url_   = fields.get("url", "")
            if title or body:
                result = f"ReliefWeb — {title}\n{body[:800]}\nSource: {url_}"
                _reliefweb_cache.set(cache_key, result)
                return result
        _reliefweb_cache.set(cache_key, "")
        return ""
    except Exception as exc:
        # Cache the miss so synthesis_node doesn't repeatedly fire failing requests
        # for the same (disaster_type, country) pair within the 30-minute TTL window.
        logger.warning("ReliefWeb unavailable for %r/%r: %s", disaster_type, country_name, exc)
        _reliefweb_cache.set(cache_key, "")
        return ""
