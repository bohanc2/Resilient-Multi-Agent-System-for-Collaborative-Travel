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
  const groupTrackColors = ["#059669", "#4f46e5", "#d97706", "#e11d48", "#0284c7"];
  const subGroupTracks: { name: string; color: string; coords: [number, number][] }[] = [];
  const trackMap = new Map<string, [number, number][]>();

  itemsToDisplay.forEach((it) => {
    const v = getVenue(it.venue_id, venuesMap);
    if (!v.lat || !v.lon || (v.lat === 0 && v.lon === 0)) return;

    const groupKey = [...it.members].sort().join(", ");
    if (!trackMap.has(groupKey)) {
      trackMap.set(groupKey, []);
    }
    trackMap.get(groupKey)!.push([v.lat, v.lon]);
  });

  let colorIdx = 0;
  trackMap.forEach((coords, groupKey) => {
    if (coords.length > 1) {
      subGroupTracks.push({
        name: groupKey,
        color: groupTrackColors[colorIdx % groupTrackColors.length],
        coords,
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

        {/* Dynamic Route Polylines */}
        {subGroupTracks.map((tr, idx) => (
          <Polyline
            key={idx}
            positions={tr.coords}
            pathOptions={{ color: tr.color, weight: 3, opacity: 0.8, dashArray: "5, 6" }}
          />
        ))}

        {/* Markers for Itinerary Venues */}
        {venuesInPlan.map(({ item, venue }, idx) => {
          if (!venue.lat || !venue.lon || (venue.lat === 0 && venue.lon === 0)) return null;

          const isAnchor = Boolean(item.is_custom || item.start >= "18:00");
          const pinColor = isAnchor
            ? "#111827"
            : groupTrackColors[idx % groupTrackColors.length];
          const label = isAnchor ? "★" : String(idx + 1);

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
                <div className="p-1 space-y-1 text-gray-900">
                  <div className="flex items-center gap-1.5 justify-between">
                    <span className="text-[10px] font-mono font-bold text-gray-500">
                      Day {item.day || 1} · Stop #{idx + 1}
                    </span>
                    <span className="text-[10px] font-semibold text-gray-700 font-mono">
                      {item.start} - {item.end}
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-gray-900">{venue.name}</h4>

                  {item.transit_from_prev && (
                    <div className="text-[10px] text-gray-600 bg-gray-50 border border-gray-200 px-1.5 py-0.5 rounded font-mono">
                      {item.transit_from_prev.mode === "walk" ? "🚶 Walk" : "🚕 Drive"} ·{" "}
                      {item.transit_from_prev.duration_mins} min from{" "}
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
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
