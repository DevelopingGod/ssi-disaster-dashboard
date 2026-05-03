export type GeoJSONPoint = {
  type: "Point";
  coordinates: [number, number];
};

export type GeoJSONPolygon = {
  type: "Polygon";
  coordinates: number[][][];
};

export type GeoJSONMultiPolygon = {
  type: "MultiPolygon";
  coordinates: number[][][][];
};

export type GeoJSONGeometry = GeoJSONPoint | GeoJSONPolygon | GeoJSONMultiPolygon;

export type DisasterType =
  | "earthquake"
  | "flood"
  | "wildfire"
  | "cyclone"
  | "tsunami"
  | "volcano"
  | "drought"
  | "landslide"
  | "storm"
  | "heatwave"
  | "coldwave"
  | "other";

export type DisasterEvent = {
  event_id: string;
  event_type: DisasterType;
  source_system: string;
  source_event_id?: string | null;
  occurred_at: string;
  reported_at?: string | null;
  location: GeoJSONGeometry;
  location_metadata?: {
    country?: string | null;
    region?: string | null;
    place_name?: string | null;
  } | null;
  severity?: {
    value?: number | null;
    unit?: string | null;
    label?: string | null;
  } | null;
  narrative_summary: string;
  affected_population?: number | null;
  tags?: string[];
  confidence_score?: number | null;
};

export type ConversationTurn = {
  role: "user" | "assistant";
  content: string;
};

export type ChatRequest = {
  query: string;
  conversation_id?: string;
  user_id?: string;
  conversation_history?: ConversationTurn[];
};

export type ChatResponse = {
  response: string;
  route_target?: string | null;
  events: DisasterEvent[];
  warnings: string[];
  guardrail_violations: string[];
  unavailable_data_reasons: string[];
  conversation_history: ConversationTurn[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  eventIds?: string[];
};
