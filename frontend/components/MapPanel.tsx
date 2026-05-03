"use client";

import { useEffect, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";

import type { DisasterEvent } from "@/lib/types";

type MapPanelProps = {
  events: DisasterEvent[];
  selectedEventId?: string | null;
};

function eventColor(eventType: DisasterEvent["event_type"]): string {
  if (eventType === "earthquake") return "#dc2626";
  if (eventType === "flood") return "#2563eb";
  if (eventType === "wildfire") return "#ea580c";
  return "#7c3aed";
}

function MapAutoZoom({ events, selectedEventId }: { events: DisasterEvent[]; selectedEventId?: string | null }) {
  const map = useMap();

  useEffect(() => {
    if (!events || events.length === 0) return;

    if (selectedEventId) {
      const selectedEvent = events.find((e) => e.event_id === selectedEventId);
      if (selectedEvent) {
        const tempGeoJson = L.geoJSON({
          type: "Feature",
          properties: {},
          geometry: selectedEvent.location,
        } as GeoJSON.GeoJsonObject);
        const bounds = tempGeoJson.getBounds();
        if (bounds.isValid()) {
          if (selectedEvent.location.type === "Point") {
            map.flyTo([selectedEvent.location.coordinates[1], selectedEvent.location.coordinates[0]], 8);
          } else {
            map.flyToBounds(bounds, { padding: [50, 50] });
          }
        }
        return;
      }
    }

    const featureCollection = {
      type: "FeatureCollection",
      features: events.map((event) => ({
        type: "Feature",
        properties: {},
        geometry: event.location,
      })),
    };

    const tempGeoJson = L.geoJSON(featureCollection as GeoJSON.GeoJsonObject);
    const bounds = tempGeoJson.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [map, events, selectedEventId]);

  return null;
}

export default function MapPanel({ events, selectedEventId }: MapPanelProps) {
  const [mapLayer, setMapLayer] = useState<"dark" | "light" | "satellite" | "terrain">("dark");

  const featureCollection = {
    type: "FeatureCollection" as const,
    features: events.map((event) => ({
      type: "Feature" as const,
      geometry: event.location,
      properties: {
        id: event.event_id,
        type: event.event_type,
        summary: event.narrative_summary,
        source: event.source_system,
      },
    })),
  };

  const disasterCounts = events.reduce((acc, event) => {
    acc[event.event_type] = (acc[event.event_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <section
      className="relative h-full w-full"
      style={{ backgroundColor: "var(--bg-primary)" }}
    >
      {/* Override Leaflet's default white popup chrome */}
      <style>{`
        .disaster-popup .leaflet-popup-content-wrapper {
          background: #0d0a08 !important;
          border: 1px solid #3a2e26 !important;
          border-radius: 0 !important;
          box-shadow: 0 4px 20px rgba(0,0,0,0.6) !important;
          padding: 0 !important;
        }
        .disaster-popup .leaflet-popup-content {
          margin: 0 !important;
        }
        .disaster-popup .leaflet-popup-tip {
          background: #0d0a08 !important;
        }
        .disaster-popup .leaflet-popup-close-button {
          color: #7a6a5e !important;
          font-size: 16px !important;
          top: 4px !important;
          right: 6px !important;
        }
        .disaster-popup .leaflet-popup-close-button:hover {
          color: #f0e8df !important;
        }
      `}</style>
      <MapContainer
        center={[20, 0]}
        zoom={2}
        minZoom={2}
        scrollWheelZoom
        className="h-full w-full z-0"
      >
        <TileLayer
          attribution={
            mapLayer === "satellite"
              ? "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
              : mapLayer === "terrain"
              ? 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
              : '&copy; <a href="https://carto.com/attributions">CARTO</a>'
          }
          url={
            mapLayer === "dark"
              ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              : mapLayer === "light"
              ? "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              : mapLayer === "satellite"
              ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              : "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
          }
        />
        <MapAutoZoom events={events} selectedEventId={selectedEventId} />
        <GeoJSON
          key={events.map((e) => e.event_id).join(",")}
          data={featureCollection}
          pointToLayer={(feature, latlng) => {
            const color = eventColor(
              (feature?.properties?.type ?? "other") as DisasterEvent["event_type"]
            );
            return L.circleMarker(latlng, {
              radius: 7,
              fillColor: color,
              color: "#120D0A",
              weight: 1.5,
              opacity: 1,
              fillOpacity: 0.88,
            });
          }}
          style={(feature) => ({
            color: eventColor(
              (feature?.properties?.type ?? "other") as DisasterEvent["event_type"]
            ),
            weight: 2,
            fillOpacity: 0.18,
          })}
          onEachFeature={(feature, layer) => {
            const summary = feature.properties?.summary ?? "No summary available.";
            const source  = feature.properties?.source  ?? "Unknown source";
            const type    = feature.properties?.type    ?? "";
            const color   = eventColor((type || "other") as DisasterEvent["event_type"]);

            // Extract lat/lon from Point geometry (coordinates are [lon, lat])
            const coords =
              feature.geometry?.type === "Point"
                ? (feature.geometry as GeoJSON.Point).coordinates
                : null;
            const latStr = coords ? coords[1].toFixed(4) : null;
            const lonStr = coords ? coords[0].toFixed(4) : null;
            const coordsRow =
              latStr && lonStr
                ? `<div style="` +
                    `margin-top:8px;` +
                    `padding-top:7px;` +
                    `border-top:1px solid #2e241e;` +
                    `display:flex;gap:10px;` +
                  `">` +
                    `<span style="color:#7a6a5e;font-size:9px;text-transform:uppercase;letter-spacing:0.14em;">Lat</span>` +
                    `<span style="color:#b0a090;font-size:9.5px;">${latStr}</span>` +
                    `<span style="color:#7a6a5e;font-size:9px;text-transform:uppercase;letter-spacing:0.14em;margin-left:4px;">Lon</span>` +
                    `<span style="color:#b0a090;font-size:9.5px;">${lonStr}</span>` +
                  `</div>`
                : "";

            layer.bindPopup(
              `<div style="` +
                `font-family:'Courier New',monospace;` +
                `font-size:11.5px;` +
                `background:#0d0a08;` +
                `color:#f0e8df;` +
                `padding:10px 12px;` +
                `border-left:3px solid ${color};` +
                `min-width:200px;` +
                `max-width:280px;` +
              `">` +
                `<div style="color:${color};font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.12em;font-size:10px;">${source}</div>` +
                `<div style="color:#e8ddd4;line-height:1.6;font-size:11px;">${summary}</div>` +
                coordsRow +
              `</div>`,
              { className: "disaster-popup" }
            );
          }}
        />
      </MapContainer>

      {/* Layer switcher */}
      <div
        className="absolute right-3 top-3 z-[1000] flex gap-px border"
        style={{ backgroundColor: "var(--border-c)", borderColor: "var(--border-c)" }}
      >
        {(["dark", "light", "satellite", "terrain"] as const).map((layer) => (
          <button
            key={layer}
            onClick={() => setMapLayer(layer)}
            className="px-2.5 py-1.5 text-[0.5625rem] font-mono uppercase tracking-widest capitalize transition-colors"
            style={
              mapLayer === layer
                ? { backgroundColor: "var(--accent)", color: "var(--bg-primary)" }
                : { backgroundColor: "var(--bg-elevated)", color: "var(--text-muted)" }
            }
          >
            {layer}
          </button>
        ))}
      </div>

      {/* Event count */}
      <div
        className="absolute right-3 top-14 z-[1000] border px-3 py-1.5 text-[0.5625rem] font-mono uppercase tracking-widest"
        style={{
          backgroundColor: "color-mix(in srgb, var(--bg-elevated) 90%, transparent)",
          borderColor: "var(--border-c)",
          color: "var(--text-muted)",
        }}
      >
        {events.length} event{events.length !== 1 ? "s" : ""} plotted
      </div>

      {/* Legend */}
      {events.length > 0 && (
        <div
          className="absolute bottom-6 left-3 z-[1000] border p-3"
          style={{
            backgroundColor: "color-mix(in srgb, var(--bg-elevated) 92%, transparent)",
            borderColor: "var(--border-c)",
          }}
        >
          <p
            className="mb-2.5 text-[0.5625rem] font-mono uppercase tracking-[0.2em]"
            style={{ color: "var(--text-muted)" }}
          >
            Event Types
          </p>
          <div className="flex flex-col gap-1.5">
            {Object.entries(disasterCounts).map(([type, count]) => (
              <div
                key={type}
                className="flex items-center gap-2 text-[0.625rem] font-mono capitalize"
                style={{ color: "var(--text-secondary)" }}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: eventColor(type as DisasterEvent["event_type"]) }}
                />
                {type} · {count}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
