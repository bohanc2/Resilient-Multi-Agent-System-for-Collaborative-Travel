"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { PlanOutput } from "../types";
import { getGroupColor, getVenue } from "../lib/venues";

interface InteractiveMapProps {
  plan: PlanOutput | null;
  selectedVenueId: string | null;
  onSelectVenue: (venueId: string) => void;
  venuesMap?: Record<string, any>;
}

// Map Controller for smooth flyTo
function MapFlyTo({
  selectedVenueId,
  venuesMap,
}: {
  selectedVenueId: string | null;
  venuesMap?: Record<string, any>;
}) {
  const map = useMap();

  useEffect(() => {
    if (!selectedVenueId) return;
    const v = getVenue(selectedVenueId, venuesMap);
    if (v.lat && v.lon) {
      map.flyTo([v.lat, v.lon], 14, {
        duration: 1.0,
        easeLinearity: 0.25,
      });
    }
  }, [selectedVenueId, map, venuesMap]);

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
}: InteractiveMapProps) {
  const venuesInPlan = (plan?.itinerary || []).map((it) => ({
    item: it,
    venue: getVenue(it.venue_id, venuesMap),
    colorMeta: getGroupColor(it.members),
  }));

  const defaultCenter: [number, number] =
    venuesInPlan.length > 0 && venuesInPlan[0].venue.lat
      ? [venuesInPlan[0].venue.lat, venuesInPlan[0].venue.lon]
      : [25.033, 121.564]; // Taipei center

  // Build route lines for tracks
  const trackCoords: Record<string, [number, number][]> = {
    hiking: [],
    art: [],
    cafe: [],
  };

  (plan?.itinerary || []).forEach((it) => {
    const v = getVenue(it.venue_id, venuesMap);
    if (!v.lat || !v.lon) return;

    if (it.members.includes("Alice") || it.members.includes("Bob")) {
      trackCoords.hiking.push([v.lat, v.lon]);
    }
    if (it.members.includes("Carol") || it.members.includes("Dave")) {
      trackCoords.art.push([v.lat, v.lon]);
    }
    if (it.members.includes("Eve") || it.members.includes("Frank")) {
      trackCoords.cafe.push([v.lat, v.lon]);
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
        <MapFlyTo selectedVenueId={selectedVenueId} venuesMap={venuesMap} />

        {/* OpenStreetMap Standard Tiles (100% Free, No API Key Required, Clean & Reliable) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Polylines for Group Tracks */}
        {trackCoords.hiking.length > 1 && (
          <Polyline positions={trackCoords.hiking} pathOptions={{ color: "#059669", weight: 3, opacity: 0.8, dashArray: "5, 6" }} />
        )}
        {trackCoords.art.length > 1 && (
          <Polyline positions={trackCoords.art} pathOptions={{ color: "#4f46e5", weight: 3, opacity: 0.8, dashArray: "5, 6" }} />
        )}
        {trackCoords.cafe.length > 1 && (
          <Polyline positions={trackCoords.cafe} pathOptions={{ color: "#d97706", weight: 3, opacity: 0.8, dashArray: "5, 6" }} />
        )}

        {/* Markers for Itinerary Venues */}
        {venuesInPlan.map(({ item, venue, colorMeta }, idx) => {
          let pinColor = "#0284c7";
          let label = "101";

          if (item.members.includes("Alice")) {
            pinColor = "#059669";
            label = "H";
          } else if (item.members.includes("Carol")) {
            pinColor = "#4f46e5";
            label = "A";
          } else if (item.members.includes("Eve")) {
            pinColor = "#d97706";
            label = "C";
          }

          if (item.venue_id === "din_tai_fung_101") {
            pinColor = "#111827";
            label = "🔒";
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
                <div className="p-1 space-y-1 text-gray-900">
                  <h4 className="text-xs font-bold text-gray-900">{venue.name}</h4>
                  <div className="flex items-center gap-1.5 text-[11px] text-gray-500">
                    <span className="font-semibold text-gray-700">
                      {item.start} - {item.end}
                    </span>
                    <span>•</span>
                    <span>{venue.indoor ? "Indoor" : "Outdoor"}</span>
                  </div>
                  <div className="text-[10px] font-medium text-gray-600 pt-0.5">
                    Track: {item.members.join(", ")}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Floating Map Legend (Bottom-Left) */}
      <div className="absolute bottom-3 left-3 z-[400] bg-white/95 backdrop-blur px-3 py-1.5 rounded-lg text-[11px] border border-gray-200 shadow-xs pointer-events-none flex items-center gap-3">
        <span className="font-semibold text-gray-700">Tracks:</span>
        <div className="flex items-center gap-1 text-gray-600">
          <span className="w-2 h-2 rounded-full bg-emerald-600" />
          <span>Hiking</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600">
          <span className="w-2 h-2 rounded-full bg-indigo-600" />
          <span>Art</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600">
          <span className="w-2 h-2 rounded-full bg-amber-600" />
          <span>Cafe</span>
        </div>
        <div className="flex items-center gap-1 text-gray-600">
          <span className="w-2 h-2 rounded-full bg-gray-900" />
          <span>Dinner Anchor</span>
        </div>
      </div>
    </div>
  );
}
