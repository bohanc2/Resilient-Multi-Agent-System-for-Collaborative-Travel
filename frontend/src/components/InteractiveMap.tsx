"use client";

import React, { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { ItineraryItem, PlanOutput } from "../types";
import { getGroupColor, getVenue } from "../lib/venues";
import { MapPin, Navigation } from "lucide-react";

interface InteractiveMapProps {
  plan: PlanOutput | null;
  selectedVenueId: string | null;
  onSelectVenue: (venueId: string) => void;
}

// Map Controller for smooth flyTo
function MapFlyTo({ selectedVenueId }: { selectedVenueId: string | null }) {
  const map = useMap();

  useEffect(() => {
    if (!selectedVenueId) return;
    const v = getVenue(selectedVenueId);
    if (v.lat && v.lon) {
      map.flyTo([v.lat, v.lon], 14, {
        duration: 1.2,
        easeLinearity: 0.25,
      });
    }
  }, [selectedVenueId, map]);

  return null;
}

// Custom DivIcon creator
function createCustomPin(color: string, label: string) {
  return L.divIcon({
    className: "custom-leaflet-marker",
    html: `
      <div style="
        background: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        border: 2px solid white;
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-size: 11px;
          font-weight: bold;
        ">${label}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
}

export default function InteractiveMap({
  plan,
  selectedVenueId,
  onSelectVenue,
}: InteractiveMapProps) {
  const defaultCenter: [number, number] = [25.042, 121.535]; // Taipei center

  const venuesInPlan = (plan?.itinerary || []).map((it) => ({
    item: it,
    venue: getVenue(it.venue_id),
    colorMeta: getGroupColor(it.members),
  }));

  // Build route lines for tracks
  const trackCoords: Record<string, [number, number][]> = {
    hiking: [],
    art: [],
    cafe: [],
  };

  (plan?.itinerary || []).forEach((it) => {
    const v = getVenue(it.venue_id);
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
    <div className="relative w-full h-full min-h-[500px] rounded-2xl overflow-hidden glass-panel border border-white/10 shadow-2xl">
      <MapContainer
        center={defaultCenter}
        zoom={12}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", minHeight: "520px", background: "#0b0f19" }}
      >
        <MapFlyTo selectedVenueId={selectedVenueId} />

        {/* CartoDB Dark Matter Tiles (Clean, modern dark SaaS aesthetic, no API key needed) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        {/* Polylines for Group Tracks */}
        {trackCoords.hiking.length > 1 && (
          <Polyline positions={trackCoords.hiking} pathOptions={{ color: "#10b981", weight: 3, opacity: 0.7, dashArray: "4, 6" }} />
        )}
        {trackCoords.art.length > 1 && (
          <Polyline positions={trackCoords.art} pathOptions={{ color: "#6366f1", weight: 3, opacity: 0.7, dashArray: "4, 6" }} />
        )}
        {trackCoords.cafe.length > 1 && (
          <Polyline positions={trackCoords.cafe} pathOptions={{ color: "#f59e0b", weight: 3, opacity: 0.7, dashArray: "4, 6" }} />
        )}

        {/* Markers for Itinerary Venues */}
        {venuesInPlan.map(({ item, venue, colorMeta }, idx) => {
          let pinColor = "#0284c7";
          let label = "101";

          if (item.members.includes("Alice")) {
            pinColor = "#10b981";
            label = "山";
          } else if (item.members.includes("Carol")) {
            pinColor = "#6366f1";
            label = "藝";
          } else if (item.members.includes("Eve")) {
            pinColor = "#f59e0b";
            label = "咖";
          }

          if (item.venue_id === "din_tai_fung_101") {
            pinColor = "#eab308";
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
                <div className="p-1 space-y-1 text-slate-900">
                  <h4 className="text-sm font-bold">{venue.name}</h4>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <span className="font-semibold text-slate-800">
                      {item.start} - {item.end}
                    </span>
                    <span>•</span>
                    <span>{venue.indoor ? "室內" : "室外"}</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-tight">
                    {venue.description}
                  </p>
                  <div className="text-[11px] font-semibold text-sky-700 pt-1">
                    成員: {item.members.join(", ")}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Floating Map Legend */}
      <div className="absolute bottom-4 left-4 z-[400] glass-card px-3 py-2 rounded-xl text-xs space-y-1.5 border border-white/10 shadow-lg pointer-events-none">
        <span className="font-bold text-slate-300 block text-[11px]">景點與移動軌跡</span>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-emerald-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span>登山組</span>
          </div>
          <div className="flex items-center gap-1.5 text-indigo-300">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" />
            <span>藝文組</span>
          </div>
          <div className="flex items-center gap-1.5 text-amber-300">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>咖啡組</span>
          </div>
          <div className="flex items-center gap-1.5 text-yellow-300">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
            <span>鎖定晚餐</span>
          </div>
        </div>
      </div>
    </div>
  );
}
