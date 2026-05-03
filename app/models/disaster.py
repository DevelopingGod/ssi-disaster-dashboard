from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class DisasterType(str, Enum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    WILDFIRE = "wildfire"
    CYCLONE = "cyclone"
    TSUNAMI = "tsunami"
    VOLCANO = "volcano"
    DROUGHT = "drought"
    LANDSLIDE = "landslide"
    STORM = "storm"
    HEATWAVE = "heatwave"
    COLDWAVE = "coldwave"
    OTHER = "other"


class GeoJSONPoint(BaseModel):
    type: Literal["Point"]
    coordinates: List[float] = Field(
        ...,
        description="GeoJSON Point coordinates in [longitude, latitude] order.",
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: List[float]) -> List[float]:
        if len(value) != 2:
            raise ValueError("Point coordinates must contain exactly [longitude, latitude].")
        lon, lat = value
        if not -180.0 <= lon <= 180.0:
            raise ValueError("Longitude must be between -180 and 180.")
        if not -90.0 <= lat <= 90.0:
            raise ValueError("Latitude must be between -90 and 90.")
        return value


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"]
    coordinates: List[List[List[float]]] = Field(
        ...,
        description=(
            "GeoJSON Polygon coordinates. "
            "First ring is outer boundary; optional additional rings are holes."
        ),
    )


class GeoJSONMultiPolygon(BaseModel):
    type: Literal["MultiPolygon"]
    coordinates: List[List[List[List[float]]]] = Field(
        ...,
        description="GeoJSON MultiPolygon coordinates.",
    )


GeoJSONGeometry = Union[GeoJSONPoint, GeoJSONPolygon, GeoJSONMultiPolygon]


class LocationMetadata(BaseModel):
    country: Optional[str] = Field(default=None, description="Country inferred or provided by source")
    region: Optional[str] = Field(default=None, description="Administrative area/state/province")
    place_name: Optional[str] = Field(default=None, description="Human-readable place label")


class Severity(BaseModel):
    value: Optional[float] = Field(
        default=None,
        description="Numeric severity indicator such as magnitude, wind speed, or index",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Severity unit, e.g. Mw, km/h, AQI",
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable severity category such as minor/moderate/severe",
    )


class DisasterEvent(BaseModel):
    event_id: str = Field(..., description="Globally unique normalized event identifier")
    event_type: DisasterType = Field(..., description="Normalized disaster category")
    source_system: str = Field(..., description="Origin system, e.g. GDACS, USGS, FIRMS, ReliefWeb")
    source_event_id: Optional[str] = Field(default=None, description="Event ID in the source system")
    occurred_at: datetime = Field(..., description="Primary event timestamp in UTC")
    reported_at: Optional[datetime] = Field(default=None, description="When source published/updated this event")
    location: GeoJSONGeometry = Field(..., description="GeoJSON geometry for event location/extent")
    location_metadata: Optional[LocationMetadata] = Field(
        default=None,
        description="Optional human-readable location metadata",
    )
    severity: Severity = Field(default_factory=Severity, description="Normalized severity details")
    narrative_summary: str = Field(..., min_length=1, description="Clean human-readable event summary")
    affected_population: Optional[int] = Field(default=None, ge=0, description="Estimated affected count")
    tags: List[str] = Field(default_factory=list, description="Search/filter tags")
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score for event fusion/classification",
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original source payload for traceability and audits",
    )

    @field_validator("narrative_summary")
    @classmethod
    def validate_narrative_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("narrative_summary cannot be blank")
        return cleaned
