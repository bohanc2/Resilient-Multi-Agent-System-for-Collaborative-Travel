"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { PlanOutput } from "../types";
import { getVenue } from "../lib/venues";

interface InteractiveMapProps {
  plan: PlanOutput | null;
  selectedVenueId: string | null;
  onSelectVenue: (venueId: string) => void;
  venuesMap?: Record<string, any>;
  activeDay?: number;
}

// Map Controller for smooth flyTo
function MapFlyTo({
  selectedVenueId,
  venuesMap,
  center,
}: {
  selectedVenueId: string | null;
  venuesMap?: Record<string, any>;
  center?: [number, number];
}) {
  const map = useMap();

  useEffect(() => {
    if (selectedVenueId) {
      const v = getVenue(selectedVenueId, venuesMap);
      if (v.lat && v.lon && (v.lat !== 0 || v.lon !== 0)) {
        map.flyTo([v.lat, v.lon], 14, {
          duration: 1.0,
          easeLinearity: 0.25,
        });
        return;
      }
    }

    if (center && (center[0] !== 0 || center[1] !== 0)) {
      map.flyTo(center, 13, { duration: 1.0 });
    }
  }, [selectedVenueId, map, venuesMap, center]);

  return null;
}

// Custom DivIcon creator (Apple Maps / Linear minimalist pin)
function createCustomPin(color: string, label: string) {
  return L.divIcon({
    className: "custom-leaflet-marker",
    html: `
      <div style="
        background: ${color};
        width: 28px;
        height: 28px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        border: 2px solid white;
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-size: 10px;
          font-weight: 700;
        ">${label}</span>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
}

// Directional arrow icon along the polyline path
function createArrowIcon(color: string, angle: number) {
  return L.divIcon({
    className: "custom-leaflet-arrow",
    html: `
      <div style="
        transform: rotate(${angle}deg);
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
      ">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="${color}" stroke="#ffffff" stroke-width="2">
          <path d="M12 2L22 20L12 16L2 20L12 2Z" />
        </svg>
      </div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function calculateBearing(p1: [number, number], p2: [number, number]): number {
  const y = Math.sin(((p2[1] - p1[1]) * Math.PI) / 180) * Math.cos((p2[0] * Math.PI) / 180);
  const x =
    Math.cos((p1[0] * Math.PI) / 180) * Math.sin((p2[0] * Math.PI) / 180) -
    Math.sin((p1[0] * Math.PI) / 180) *
      Math.cos((p2[0] * Math.PI) / 180) *
      Math.cos(((p2[1] - p1[1]) * Math.PI) / 180);
  return (Math.atan2(y, x) * 180) / Math.PI;
}

export default function InteractiveMap({
  plan,
  selectedVenueId,
  onSelectVenue,
  venuesMap,
  activeDay = 1,
}: InteractiveMapProps) {
  // Filter items for the active day
  const rawItems = plan?.itinerary || [];
  const activeItems = rawItems.filter((it) => (it.day || 1) === activeDay);
  const itemsToDisplay = activeItems.length > 0 ? activeItems : rawItems;

  const venuesInPlan = itemsToDisplay.map((it) => ({
    item: it,
    venue: getVenue(it.venue_id, venuesMap),
  }));

  // Determine city center coordinates
  const validVenues = venuesInPlan.filter(
    (vp) => vp.venue.lat && vp.venue.lon && (vp.venue.lat !== 0 || vp.venue.lon !== 0)
  );

  let defaultCenter: [number, number] = [25.033, 121.564];
  if (validVenues.length > 0) {
    defaultCenter = [validVenues[0].venue.lat, validVenues[0].venue.lon];
  } else if (plan?.center && plan.center[0] !== 0) {
    defaultCenter = [plan.center[0], plan.center[1]];
  } else if (venuesMap && Object.values(venuesMap).length > 0) {
    const firstV = Object.values(venuesMap).find((v) => v.lat && v.lon);
    if (firstV) {
      defaultCenter = [firstV.lat, firstV.lon];
    }
  }

  // Dynamic route polylines grouped by member sub-groups
  const groupTrackColors = ["#059669", "#4f46e5", "#d97706", "#9333ea", "#0284c7"];
  const subGroupTracks: {
    name: string;
    color: string;
    coords: [number, number][];
    arrows: { pos: [number, number]; angle: number }[];
  }[] = [];
  const trackMap = new Map<string, { coords: [number, number][]; items: typeof itemsToDisplay }>();

  itemsToDisplay.forEach((it) => {
    const v = getVenue(it.venue_id, venuesMap);
    if (!v.lat || !v.lon || (v.lat === 0 && v.lon === 0)) return;

    const groupKey = [...it.members].sort().join(", ");
    if (!trackMap.has(groupKey)) {
      trackMap.set(groupKey, { coords: [], items: [] });
    }
    trackMap.get(groupKey)!.coords.push([v.lat, v.lon]);
    trackMap.get(groupKey)!.items.push(it);
  });

  let colorIdx = 0;
  trackMap.forEach(({ coords }, groupKey) => {
    if (coords.length > 1) {
      const arrows: { pos: [number, number]; angle: number }[] = [];
      for (let i = 0; i < coords.length - 1; i++) {
        const p1 = coords[i];
        const p2 = coords[i + 1];
        const mid: [number, number] = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2];
        const angle = calculateBearing(p1, p2);
        arrows.push({ pos: mid, angle });
      }

      subGroupTracks.push({
        name: groupKey,
        color: groupTrackColors[colorIdx % groupTrackColors.length],
        coords,
        arrows,
      });
      colorIdx++;
    }
  });

  return (
    <div className="relative w-full h-full min-h-[550px] rounded-xl overflow-hidden border border-gray-200 shadow-xs bg-white">
      <MapContainer
        center={defaultCenter}
        zoom={13}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", minHeight: "550px", background: "#f8fafc" }}
      >
        <MapFlyTo selectedVenueId={selectedVenueId} venuesMap={venuesMap} center={defaultCenter} />

        {/* OpenStreetMap Standard Tiles (100% Free, Clean & Reliable) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Dynamic Route Polylines with Color Coding */}
        {subGroupTracks.map((tr, idx) => (
          <React.Fragment key={`track-${idx}`}>
            <Polyline
              positions={tr.coords}
              pathOptions={{ color: tr.color, weight: 3.5, opacity: 0.85 }}
            />
            {/* Directional SVG Arrows along the track path */}
            {tr.arrows.map((arr, aIdx) => (
              <Marker
                key={`arrow-${idx}-${aIdx}`}
                position={arr.pos}
                icon={createArrowIcon(tr.color, arr.angle)}
                interactive={false}
              />
            ))}
          </React.Fragment>
        ))}

        {/* Markers for Itinerary Venues with Sequence Labels (S, 1, 2, ..., E, ★) */}
        {venuesInPlan.map(({ item, venue }, idx) => {
          if (!venue.lat || !venue.lon || (venue.lat === 0 && venue.lon === 0)) return null;

          const isSharedAnchor = Boolean(item.is_shared || item.members.length >= 4 || item.start >= "18:00");
          const trackIdx = subGroupTracks.findIndex((tr) =>
            tr.name === [...item.members].sort().join(", ")
          );
          const pinColor = isSharedAnchor
            ? "#111827"
            : groupTrackColors[(trackIdx >= 0 ? trackIdx : idx) % groupTrackColors.length];

          // Determine label: S for first stop, ★ for evening convergence, or sequential number
          let label = String(idx + 1);
          if (isSharedAnchor) {
            label = "★";
          } else if (idx === 0) {
            label = "S";
          } else if (idx === venuesInPlan.length - 1) {
            label = "E";
          }

          return (
            <Marker
              key={`${item.venue_id}-${idx}`}
              position={[venue.lat, venue.lon]}
              icon={createCustomPin(pinColor, label)}
              eventHandlers={{
                click: () => onSelectVenue(item.venue_id),
              }}
            >
              <Popup className="custom-leaflet-popup">
                <div className="p-1 space-y-1.5 text-gray-900 min-w-[180px]">
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="text-[10px] font-mono font-bold text-gray-500">
                      Day {item.day || 1} · {label === "S" ? "Start" : label === "E" ? "End" : label === "★" ? "Regroup" : `Stop #${label}`}
                    </span>
                    <span className="text-[10px] font-semibold text-gray-700 font-mono">
                      {item.start} - {item.end}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-gray-900">{venue.name}</h4>

                  {item.transit_from_prev && (
                    <div className="text-[10px] text-gray-600 bg-gray-50 border border-gray-200 px-1.5 py-0.5 rounded font-mono">
                      {item.transit_from_prev.mode === "walk"
                        ? "🚶 Walk"
                        : item.transit_from_prev.mode === "transit"
                        ? "🚇 MRT"
                        : "🚕 Drive"}{" "}
                      · {item.transit_from_prev.duration_mins} min from{" "}
                      {item.transit_from_prev.from_venue_name || "previous"}
                    </div>
                  )}

                  <div className="flex items-center gap-1.5 text-[11px] text-gray-500 pt-0.5">
                    <span>${venue.cost} / person</span>
                    <span>•</span>
                    <span>{venue.indoor ? "Indoor" : "Outdoor"}</span>
                  </div>

                  <div className="text-[10px] font-medium text-gray-600 pt-0.5">
                    Members: {item.members.join(", ")}
                  </div>

                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                      `${venue.name} ${venue.city || ""}`
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 block text-center py-1 px-2 rounded-md bg-gray-900 text-white text-[10px] font-semibold hover:bg-gray-800 transition-colors shadow-2xs"
                  >
                    Open in Google Maps ↗
                  </a>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
