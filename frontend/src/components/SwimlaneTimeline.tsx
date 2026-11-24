"use client";

import React, { useState } from "react";
import {
  Lock,
  Clock,
  Users,
  MapPin,
  CheckCheck,
  Sun,
  CloudRain,
  Plus,
  MessageSquare,
  Calendar,
  ExternalLink,
} from "lucide-react";
import { ItineraryItem, PlanOutput, Traveler } from "../types";
import { getVenue } from "../lib/venues";

interface SwimlaneTimelineProps {
  plan: PlanOutput | null;
  travelers: Traveler[];
  selectedVenueId: string | null;
  onSelectVenue: (venueId: string) => void;
  replanModifiedVenueIds: string[];
  venuesMap?: Record<string, any>;
  onOpenAddStop?: () => void;
  activeDay?: number;
  onDayChange?: (day: number) => void;
}

const toMin = (timeStr: string): number => {
  if (!timeStr) return 540;
  const parts = timeStr.split(":");
  const h = parseInt(parts[0], 10) || 0;
  const m = parseInt(parts[1], 10) || 0;
  return h * 60 + m;
};

const getRow = (timeStr: string): number => {
  const mins = toMin(timeStr);
  // Base time 09:00 = 540 min. 15 min per row slot. Row 1 is header row.
  const slot = Math.floor((mins - 540) / 15);
  return Math.max(2, Math.min(54, slot + 2));
};

export default function SwimlaneTimeline({
  plan,
  travelers,
  selectedVenueId,
  onSelectVenue,
  replanModifiedVenueIds,
  venuesMap,
  onOpenAddStop,
  activeDay: propActiveDay,
  onDayChange,
}: SwimlaneTimelineProps) {
  const [internalDay, setInternalDay] = useState(1);
  const activeDay = propActiveDay !== undefined ? propActiveDay : internalDay;

  const handleSetActiveDay = (d: number) => {
    setInternalDay(d);
    if (onDayChange) onDayChange(d);
  };

  if (!plan || !plan.itinerary || plan.itinerary.length === 0) {
    return null;
  }

  const allItems = plan.itinerary;
  const totalDays = Math.max(
    1,
    plan.total_days || 1,
    plan.days || 1,
    plan.duration_days || 1,
    ...allItems.map((it) => it.day || 1)
  );
  const totalTravelers = travelers.length || 1;

  // Filter items for the selected day
  const dayItems = allItems.filter((it) => (it.day || 1) === activeDay);

  // 1. Identify shared activities vs split sub-tracks for the current day
  const isShared = (it: ItineraryItem) => {
    if (it.is_shared) return true;
    if (it.members.length >= totalTravelers) return true;
    if (
      it.venue_id === "din_tai_fung_101" ||
      it.venue_id.includes("dinner") ||
      (it.venue_id.includes("market") && it.start >= "18:00")
    ) {
      return true;
    }
    const v = getVenue(it.venue_id, venuesMap);
    if (
      (v.tags?.includes("dining") ||
        v.tags?.includes("food") ||
        v.tags?.includes("night_market")) &&
      it.start >= "18:00"
    ) {
      return true;
    }
    return false;
  };

  const splitItems = dayItems.filter((it) => !isShared(it));

  // 2. Dynamic grouping of split items into distinct sub-tracks (1..N)
  const colors: ("emerald" | "indigo" | "amber" | "rose")[] = [
    "emerald",
    "indigo",
    "amber",
    "rose",
  ];
  const memberGroupMap = new Map<string, string[]>();

  for (const it of splitItems) {
    const key = [...it.members].sort().join(", ");
    if (!memberGroupMap.has(key)) {
      memberGroupMap.set(key, [...it.members]);
    }
  }

  let tracks: {
    id: number;
    label: string;
    members: string[];
    color: "emerald" | "indigo" | "amber" | "rose";
  }[] = [];

  if (memberGroupMap.size > 0) {
    let idx = 0;
    memberGroupMap.forEach((members) => {
      tracks.push({
        id: idx + 1,
        label: `Track ${idx + 1}`,
        members,
        color: colors[idx % colors.length],
      });
      idx++;
    });

    const covered = new Set(tracks.flatMap((t) => t.members));
    const uncovered = travelers.filter((t) => !covered.has(t.name));
    if (uncovered.length > 0) {
      tracks.push({
        id: tracks.length + 1,
        label: `Track ${tracks.length + 1}`,
        members: uncovered.map((t) => t.name),
        color: colors[tracks.length % colors.length],
      });
    }
  } else {
    tracks = [
      {
        id: 1,
        label: "Track 1",
        members: travelers.map((t) => t.name),
        color: "indigo",
      },
    ];
  }

  // 3. Deduplication of day items to prevent duplicates and enable column spanning
  interface RenderItem extends ItineraryItem {
    idKey: string;
  }

  const mergedItems: RenderItem[] = [];
  const itemMap = new Map<string, RenderItem>();

  for (const it of dayItems) {
    const key = `${it.venue_id}_${it.start}_${it.end}`;
    if (!itemMap.has(key)) {
      const copy: RenderItem = {
        ...it,
        idKey: key,
        members: [...it.members],
        day: it.day || 1,
      };
      itemMap.set(key, copy);
      mergedItems.push(copy);
    } else {
      const existing = itemMap.get(key)!;
      const combined = Array.from(new Set([...existing.members, ...it.members]));
      existing.members = combined;
      if (it.is_shared) existing.is_shared = true;
      if (it.note && !existing.note) existing.note = it.note;
    }
  }

  // Helper to compute column placement
  const getColumnPlacement = (item: RenderItem) => {
    const isFullShared =
      item.is_shared ||
      item.members.length >= totalTravelers ||
      item.venue_id === "din_tai_fung_101" ||
      item.venue_id.includes("dinner") ||
      (getVenue(item.venue_id, venuesMap).tags?.includes("dining") && item.start >= "18:00");

    if (isFullShared || tracks.length <= 1) {
      return { colStart: 2, colEnd: tracks.length + 2, isFullShared: true };
    }

    const matchedCols: number[] = [];
    tracks.forEach((track, tIdx) => {
      const colIndex = tIdx + 2;
      if (track.members.some((m) => item.members.includes(m))) {
        matchedCols.push(colIndex);
      }
    });

    if (matchedCols.length > 0) {
      const minCol = Math.min(...matchedCols);
      const maxCol = Math.max(...matchedCols);
      return { colStart: minCol, colEnd: maxCol + 1, isFullShared: false };
    }

    return { colStart: 2, colEnd: tracks.length + 2, isFullShared: true };
  };

  const calculateSpending = (name: string) => {
    let spent = 0;
    allItems.forEach((it) => {
      if (it.members.includes(name)) {
        const v = getVenue(it.venue_id, venuesMap);
        spent += v.cost;
      }
    });
    return spent;
  };

  // Find local hotel for morning basecamp
  const firstItem = dayItems[0];
  const hotelId =
    firstItem?.transit_from_prev?.from_venue_id ||
    Object.keys(venuesMap || {}).find((k) => k.includes("hotel")) ||
    "hotel";
  const hotelVenue = getVenue(hotelId, venuesMap);

  const borderColors = {
    emerald: "border-emerald-600",
    indigo: "border-indigo-600",
    amber: "border-amber-600",
    rose: "border-rose-600",
  };
  const dotColors = {
    emerald: "bg-emerald-600",
    indigo: "bg-indigo-600",
    amber: "bg-amber-600",
    rose: "bg-rose-600",
  };
  const badgeColors = {
    emerald: "text-emerald-700 bg-emerald-50 border border-emerald-200",
    indigo: "text-indigo-700 bg-indigo-50 border border-indigo-200",
    amber: "text-amber-700 bg-amber-50 border border-amber-200",
    rose: "text-rose-700 bg-rose-50 border border-rose-200",
  };

  return (
    <div className="space-y-5">
      {/* 1. Header with Add Custom Stop Button */}
      <div className="flex items-center justify-between pb-1 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
            Multi-Track Timeline
          </span>
          <span className="text-[11px] text-gray-500 font-mono">
            Day {activeDay} of {totalDays} · {dayItems.length} Stops ({allItems.length} Total across {totalDays} {totalDays === 1 ? "Day" : "Days"})
          </span>
        </div>
        {onOpenAddStop && (
          <button
            type="button"
            onClick={onOpenAddStop}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold shadow-xs transition-all active:scale-[0.98]"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Custom Stop</span>
          </button>
        )}
      </div>

      {/* 2. Day Switcher Tabs */}
      {totalDays > 1 && (
        <div className="flex items-center justify-between p-1 bg-gray-100 rounded-xl border border-gray-200">
          <div className="flex items-center gap-1">
            {Array.from({ length: totalDays }, (_, i) => i + 1).map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => handleSetActiveDay(d)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  activeDay === d
                    ? "bg-white text-gray-900 shadow-xs"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-200/60"
                }`}
              >
                Day {d}
              </button>
            ))}
          </div>
          <span className="text-[11px] font-medium text-gray-500 px-2 font-mono">
            Day {activeDay}: {dayItems.length} activities
          </span>
        </div>
      )}

      {/* 3. Traveler Limit & Budget Tracker */}
      <div className="minimal-panel rounded-xl p-3.5 space-y-2.5">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span className="font-semibold text-gray-800 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-gray-700" />
            <span>Group Budget & Fatigue Monitor</span>
          </span>
          <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            All {totalTravelers} Within Budget
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          {travelers.map((t) => {
            const spent = calculateSpending(t.name);
            const pct = Math.min(100, Math.round((spent / t.budget) * 100));

            return (
              <div
                key={t.name}
                className="p-2 rounded-lg bg-gray-50 border border-gray-100 space-y-1"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span
                    className="font-bold text-gray-800 truncate max-w-[80px]"
                    title={t.name}
                  >
                    {t.name}
                  </span>
                  <span className="text-gray-500 font-mono">
                    ${spent}/${t.budget}
                  </span>
                </div>
                <div className="w-full h-1 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      pct > 90 ? "bg-amber-500" : "bg-gray-800"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. True 2D CSS Grid Timeline (ALL Tracks Strictly Side-by-Side in ONE Row) */}
      <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white p-3 shadow-xs">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `72px repeat(${tracks.length}, minmax(220px, 1fr))`,
            gridTemplateRows: `44px repeat(52, 24px)`,
            minWidth: `${72 + tracks.length * 240}px`,
            position: "relative",
          }}
        >
          {/* Row 1 Header: Time Axis Column */}
          <div
            style={{ gridColumn: "1 / 2", gridRow: "1 / 2" }}
            className="h-11 flex items-center justify-center border-b border-gray-200 bg-gray-50/80 rounded-tl-xl text-[11px] font-bold text-gray-500 uppercase tracking-wider"
          >
            Time
          </div>

          {/* Row 1 Header: Tracks 1..N */}
          {tracks.map((track, idx) => (
            <div
              key={`track-header-${idx}`}
              style={{
                gridColumn: `${idx + 2} / ${idx + 3}`,
                gridRow: "1 / 2",
              }}
              className={`h-11 px-3 flex items-center justify-between border-b-2 ${
                borderColors[track.color]
              } bg-gray-50/50 ${
                idx === tracks.length - 1 ? "rounded-tr-xl" : ""
              }`}
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className={`w-2 h-2 rounded-full ${dotColors[track.color]} shrink-0`}
                />
                <span className="text-xs font-bold uppercase tracking-wide text-gray-900 truncate">
                  {track.label}
                </span>
              </div>
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                  badgeColors[track.color]
                } truncate shrink-0 max-w-[140px]`}
              >
                {track.members.join(", ")}
              </span>
            </div>
          ))}

          {/* Vertical Track Column Divider Guidelines */}
          {tracks.map((_, idx) => (
            <div
              key={`track-divider-${idx}`}
              style={{
                gridColumn: `${idx + 2} / ${idx + 3}`,
                gridRow: "2 / -1",
              }}
              className={`border-r border-gray-100/70 pointer-events-none ${
                idx === tracks.length - 1 ? "border-r-0" : ""
              }`}
            />
          ))}

          {/* Time Axis Labels (Col 1) and Hourly Horizontal Guidelines (Col 2 / -1) */}
          {Array.from({ length: 14 }, (_, i) => i + 9).map((h) => {
            const timeStr = `${String(h).padStart(2, "0")}:00`;
            const row = getRow(timeStr);
            return (
              <React.Fragment key={`time-axis-${h}`}>
                {/* Time Label in Column 1 */}
                <div
                  style={{
                    gridColumn: "1 / 2",
                    gridRow: `${row} / ${row + 4}`,
                  }}
                  className="px-2 pt-1 border-r border-gray-200 text-[11px] font-mono text-gray-400 select-none flex items-start justify-end pr-2"
                >
                  {timeStr}
                </div>

                {/* Hourly Guideline Line across All Tracks */}
                <div
                  style={{
                    gridColumn: "2 / -1",
                    gridRow: `${row} / ${row + 1}`,
                  }}
                  className="border-t border-gray-100/80 pointer-events-none -mt-[1px]"
                />
              </React.Fragment>
            );
          })}

          {/* Morning Hotel Basecamp Departure (09:00 - 09:30, Rows 2 / 4, Spans 2 / -1) */}
          <div
            style={{
              gridColumn: "2 / -1",
              gridRow: "2 / 4",
              zIndex: 5,
            }}
            className="p-1"
          >
            <div
              onClick={() => onSelectVenue(hotelId)}
              className="h-full rounded-xl px-3 py-1.5 bg-gray-50 border border-gray-200 flex items-center justify-between cursor-pointer hover:border-gray-400 hover:bg-gray-100/70 transition-all shadow-2xs"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-6 h-6 rounded-md bg-gray-200/80 flex items-center justify-center text-gray-700 shrink-0">
                  <MapPin className="w-3.5 h-3.5" />
                </div>
                <div className="flex items-center gap-2 truncate">
                  <span className="text-xs font-mono font-bold text-gray-800 shrink-0">
                    09:30
                  </span>
                  <span className="text-xs font-semibold text-gray-900 truncate">
                    {hotelVenue.name || "Hotel Basecamp"}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-white text-gray-600 border border-gray-200 shrink-0 font-medium hidden sm:inline">
                    All {totalTravelers} Members
                  </span>
                </div>
              </div>
              <span className="text-[11px] text-gray-400 font-mono shrink-0 hidden md:inline">
                Day {activeDay} Synchronized Departure
              </span>
            </div>
          </div>

          {/* 18:15 Regroup Convergence Divider (Row 39 / 40, Spans 2 / -1) */}
          <div
            style={{
              gridColumn: "2 / -1",
              gridRow: "39 / 40",
              zIndex: 10,
            }}
            className="flex items-center justify-center pointer-events-none px-2"
          >
            <div className="w-full flex items-center justify-center relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-dashed border-gray-300" />
              </div>
              <div className="relative px-3 py-0.5 bg-white rounded-full border border-gray-300 text-[11px] font-semibold text-gray-700 flex items-center gap-1.5 shadow-xs pointer-events-auto">
                <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>18:15 Regroup Convergence (Arrival gap ≤ 15 min PASS)</span>
              </div>
            </div>
          </div>

          {/* Activity Cards Placed Directly in 2D CSS Grid */}
          {mergedItems
            .filter((item) => !(item.venue_id === hotelId && item.start <= "09:30"))
            .map((item, idx) => {
              const { colStart, colEnd, isFullShared } = getColumnPlacement(item);
              const startRow = getRow(item.start);
              let endRow = getRow(item.end);
              if (endRow <= startRow) {
                endRow = startRow + 1;
              }

              const isSelected = selectedVenueId === item.venue_id;
              const isModified = replanModifiedVenueIds.includes(item.venue_id);

              const trackIdx = colStart - 2;
              const accentColor = tracks[trackIdx]?.color || "indigo";

              return (
                <div
                  key={`activity-${item.idKey}-${idx}`}
                  style={{
                    gridColumn: isFullShared ? "2 / -1" : `${colStart} / ${colEnd}`,
                    gridRow: `${startRow} / ${endRow}`,
                    zIndex: isSelected ? 20 : 5,
                  }}
                  className="p-1"
                >
                  <TimelineCard
                    item={item}
                    isSelected={isSelected}
                    onSelect={() => onSelectVenue(item.venue_id)}
                    venuesMap={venuesMap}
                    accentColor={accentColor}
                    isShared={isFullShared}
                    isModified={isModified}
                  />
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
}

// Minimalist Activity Card (Restrained, Apple/Linear style)
function TimelineCard({
  item,
  isSelected,
  onSelect,
  isModified,
  venuesMap,
  accentColor,
  isShared,
}: {
  item: ItineraryItem;
  isSelected: boolean;
  onSelect: () => void;
  isModified?: boolean;
  venuesMap?: Record<string, any>;
  accentColor: "emerald" | "indigo" | "amber" | "rose";
  isShared?: boolean;
}) {
  const v = getVenue(item.venue_id, venuesMap);
  const transit = item.transit_from_prev;
  const isDinnerAnchor =
    isShared &&
    (item.start >= "18:00" ||
      item.venue_id === "din_tai_fung_101" ||
      item.venue_id.includes("dinner"));

  const borderLeftColors = {
    emerald: "border-l-4 border-l-emerald-600",
    indigo: "border-l-4 border-l-indigo-600",
    amber: "border-l-4 border-l-amber-600",
    rose: "border-l-4 border-l-rose-600",
  };

  return (
    <div
      onClick={onSelect}
      className={`h-full w-full rounded-xl p-2.5 flex flex-col justify-between overflow-hidden cursor-pointer select-none transition-all ${
        isDinnerAnchor
          ? "border-2 border-gray-900 bg-white shadow-sm hover:border-black"
          : isSelected
          ? "border-gray-900 ring-1 ring-gray-900 bg-white shadow-sm"
          : isModified
          ? "border-2 border-amber-500 bg-amber-50/50 shadow-sm"
          : isShared
          ? "bg-gray-50 border border-gray-200 hover:border-gray-400"
          : `bg-white border border-gray-200 hover:border-gray-300 ${borderLeftColors[accentColor]} shadow-2xs`
      }`}
    >
      <div className="space-y-1 min-w-0">
        {/* Transit pill if available */}
        {transit && (
          <div className="flex items-center gap-1 text-[10px] text-gray-500 font-mono truncate">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0" />
            <span className="font-semibold text-gray-700 truncate">
              {transit.mode === "walk"
                ? "🚶 Walk"
                : transit.mode === "transit"
                ? "🚇 Transit"
                : "🚕 Drive"}{" "}
              {transit.duration_mins}m
            </span>
            <span className="text-gray-400 truncate hidden sm:inline">
              from {transit.from_venue_name || "prev"}
            </span>
          </div>
        )}

        {/* Time & Indoor/Outdoor badge */}
        <div className="flex items-center justify-between gap-1 text-[11px]">
          <span className="font-mono font-bold text-gray-900 flex items-center gap-1 shrink-0">
            <Clock className="w-3 h-3 text-gray-400" />
            {item.start} - {item.end}
          </span>
          <div className="flex items-center gap-1 shrink-0">
            {isDinnerAnchor ? (
              <span className="flex items-center gap-1 px-1.5 py-0.2 rounded-full bg-gray-900 text-white text-[9px] font-bold">
                <Lock className="w-2.5 h-2.5 text-amber-400" />
                Dinner Anchor
              </span>
            ) : isShared ? (
              <span className="px-1.5 py-0.2 rounded bg-gray-200 text-gray-700 text-[9px] font-bold">
                Shared
              </span>
            ) : (
              <span className="text-[10px] font-medium text-gray-500 flex items-center gap-0.5">
                {v.indoor ? (
                  <Sun className="w-2.5 h-2.5 text-gray-400" />
                ) : (
                  <CloudRain className="w-2.5 h-2.5 text-gray-400" />
                )}
                {v.indoor ? "Indoor" : "Outdoor"}
              </span>
            )}
            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                `${v.name} ${v.city || ""}`
              )}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="p-0.5 text-gray-400 hover:text-gray-900 rounded transition-colors"
              title="Google Maps"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Venue Name */}
        <h5 className="text-xs font-bold text-gray-900 truncate">{v.name}</h5>

        {v.description && (
          <p className="text-[11px] text-gray-500 line-clamp-1 hidden sm:block">
            {v.description}
          </p>
        )}
      </div>

      {/* Footer: Members & Cost */}
      <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1 border-t border-gray-100 mt-1">
        <span className="font-medium text-gray-600 truncate max-w-[140px]">
          {isShared ? "All Members" : item.members.join(", ")}
        </span>
        <span className="font-semibold text-gray-700 shrink-0">${v.cost}</span>
      </div>
    </div>
  );
}
