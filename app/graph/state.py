from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.disaster import DisasterEvent


RouteTarget = Literal["live_tools", "historical_rag", "hybrid", "clarification_needed"]


class AgentState(BaseModel):
    """
    Core LangGraph state carried between routing, retrieval, and synthesis nodes.
    """

    # User interaction context
    user_query: str = Field(..., min_length=1)
    conversation_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    requested_at: datetime = Field(default_factory=datetime.utcnow)

    # Router output
    route_target: Optional[RouteTarget] = Field(default=None)
    route_reasoning: Optional[str] = Field(default=None)
    intent: Optional[str] = Field(default=None)
    geographic_filter: Optional[str] = Field(default=None)

    # Tool planning / execution context (for dynamic OpenAPI tool registry phase)
    selected_tools: List[str] = Field(default_factory=list)
    tool_arguments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    tool_results: Dict[str, Any] = Field(default_factory=dict)
    tool_errors: List[str] = Field(default_factory=list)

    # Historical retrieval context (Supabase/pgvector phase)
    rag_query: Optional[str] = Field(default=None)
    rag_context_chunks: List[str] = Field(default_factory=list)

    # Normalized synthesis output
    normalized_events: List[DisasterEvent] = Field(default_factory=list)
    synthesis_summary: Optional[str] = Field(default=None)
    warnings: List[str] = Field(default_factory=list)

    # Guardrail and failure reporting
    guardrail_violations: List[str] = Field(default_factory=list)
    unavailable_data_reasons: List[str] = Field(default_factory=list)

    # Conversation memory — list of {"role": "user"|"assistant", "content": "..."}
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)

    # Specific disaster type the user asked about, e.g. "flood", "earthquake", "cyclone".
    # None means the user asked about all types.
    requested_disaster_type: Optional[str] = Field(default=None)

    # When the user asked about 2+ specific types simultaneously, e.g.
    # "earthquakes AND cyclones" → ["earthquake", "cyclone"].
    # Empty list = all types (no type restriction on the map).
    requested_disaster_types: List[str] = Field(default_factory=list)
