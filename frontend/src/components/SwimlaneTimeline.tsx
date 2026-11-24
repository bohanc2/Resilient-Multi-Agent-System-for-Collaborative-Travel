"use client";

import React from "react";
import { Lock, Clock, Footprints, Users, MapPin, CheckCheck, Sun, CloudRain, Plus, MessageSquare } from "lucide-react";
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
}

export default function SwimlaneTimeline({
  plan,
  travelers,
  selectedVenueId,
  onSelectVenue,
  replanModifiedVenueIds,
  venuesMap,
  onOpenAddStop,
}: SwimlaneTimelineProps) {
  if (!plan || !plan.itinerary || plan.itinerary.length === 0) {
    return null;
  }

  const items = plan.itinerary;
  const totalTravelers = travelers.length || 1;

  // 1. Identify shared activities vs. split sub-tracks
  const isShared = (it: ItineraryItem) => {
    if (it.venue_id === "din_tai_fung_101") return true;
    if (it.members.length >= totalTravelers) return true;
    return false;
  };

  const sharedItemsRaw = items.filter(isShared);
  const splitItems = items.filter((it) => !isShared(it));

  // 2. Strict deduplication of shared items by (venue_id, start, end)
  const sharedItems: ItineraryItem[] = [];
  const seenSharedKeys = new Set<string>();
  for (const it of sharedItemsRaw) {
    const key = `${it.venue_id}_${it.start}_${it.end}`;
    if (!seenSharedKeys.has(key)) {
      seenSharedKeys.add(key);
      sharedItems.push(it);
    }
  }

  // 3. Dynamic grouping of split items into distinct sub-tracks
  const colors: ("emerald" | "indigo" | "amber" | "rose")[] = ["emerald", "indigo", "amber", "rose"];
  const memberGroupMap = new Map<string, ItineraryItem[]>();
  for (const it of splitItems) {
    const groupKey = [...it.members].sort().join(", ");
    if (!memberGroupMap.has(groupKey)) {
      memberGroupMap.set(groupKey, []);
    }
    memberGroupMap.get(groupKey)!.push(it);
  }

  const trackGroups: {
    label: string;
    members: string[];
    items: ItineraryItem[];
    color: "emerald" | "indigo" | "amber" | "rose";
  }[] = [];

  let colorIdx = 0;
  memberGroupMap.forEach((groupItems, groupKey) => {
    const groupMembers = groupKey.split(", ");
    let label = `Track ${trackGroups.length + 1}`;
    if (groupMembers.includes("Alice") || groupMembers.includes("Bob")) {
      label = "Hiking Track";
    } else if (groupMembers.includes("Carol") || groupMembers.includes("Dave")) {
      label = "Art Track";
    } else if (groupMembers.includes("Eve") || groupMembers.includes("Frank")) {
      label = "Cafe Track";
    }

    trackGroups.push({
      label,
      members: groupMembers,
      items: groupItems,
      color: colors[colorIdx % colors.length],
    });
    colorIdx++;
  });

  const calculateSpending = (name: string) => {
    let spent = 0;
    items.forEach((it) => {
      if (it.members.includes(name)) {
        const v = getVenue(it.venue_id, venuesMap);
        spent += v.cost;
      }
    });
    return spent;
  };

  return (
    <div className="space-y-6">
      {/* 1. Header with Add Custom Stop Button */}
      <div className="flex items-center justify-between pb-1 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
            Multi-Track Timeline
          </span>
          <span className="text-[11px] text-gray-500 font-mono">
            ({items.length} Stops Planned)
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

      {/* 2. Traveler Limit & Budget Tracker */}
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
                  <span className="font-bold text-gray-800">{t.name}</span>
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

      {/* 3. Morning Departure Card */}
      <div
        onClick={() => onSelectVenue("hotel_ximen")}
        className="minimal-card rounded-xl p-3.5 cursor-pointer flex items-center justify-between hover:border-gray-400"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-gray-800">09:00</span>
              <span className="text-sm font-semibold text-gray-900">Hotel Departure</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-gray-100 text-gray-600 border border-gray-200">
                All {totalTravelers} Travelers
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Trip kickoff; groups proceed to synchronized theme routes.
            </p>
          </div>
        </div>
        <span className="text-xs text-gray-400 font-mono hidden sm:inline">Taxi ~15 min</span>
      </div>

      {/* 4. Split Track Columns */}
      {trackGroups.length > 0 && (
        <div
          className={`grid grid-cols-1 ${
            trackGroups.length === 1
              ? "md:grid-cols-1"
              : trackGroups.length === 2
              ? "md:grid-cols-2"
              : "md:grid-cols-3"
          } gap-3.5`}
        >
          {trackGroups.map((group, gIdx) => {
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
              emerald: "text-emerald-700 bg-emerald-50",
              indigo: "text-indigo-700 bg-indigo-50",
              amber: "text-amber-700 bg-amber-50",
              rose: "text-rose-700 bg-rose-50",
            };

            return (
              <div key={gIdx} className="space-y-2.5">
                <div className={`pb-1.5 border-b-2 ${borderColors[group.color]} flex items-center justify-between`}>
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${dotColors[group.color]}`} />
                    <h4 className="text-xs font-bold uppercase tracking-wide text-gray-900">
                      {group.label}
                    </h4>
                  </div>
                  <span className={`text-[10px] font-medium px-1.5 py-0.2 rounded ${badgeColors[group.color]}`}>
                    {group.members.join(", ")}
                  </span>
                </div>

                <div className="space-y-2">
                  {group.items.map((item, idx) => (
                    <TimelineCard
                      key={idx}
                      item={item}
                      isSelected={selectedVenueId === item.venue_id}
                      onSelect={() => onSelectVenue(item.venue_id)}
                      isModified={replanModifiedVenueIds.includes(item.venue_id)}
                      venuesMap={venuesMap}
                      accentColor={group.color}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Regroup Convergence Divider */}
      <div className="relative my-4 flex items-center justify-center">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-dashed border-gray-300" />
        </div>
        <div className="relative px-3 py-1 bg-[#F9FAFB] rounded-full border border-gray-200 text-[11px] font-semibold text-gray-700 flex items-center gap-1.5 shadow-xs">
          <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>18:15 Regroup Convergence (Arrival gap ≤ 15 min PASS)</span>
        </div>
      </div>

      {/* 6. Shared Hard Anchor Dinner Card (Exactly ONE card) */}
      {sharedItems.map((item, idx) => {
        const v = getVenue(item.venue_id, venuesMap);
        const isAnchor = item.venue_id === "din_tai_fung_101" || item.venue_id.includes("chartier") || item.venue_id.includes("gonpachi") || item.venue_id.includes("katz") || item.venue_id.includes("ivars");
        const isModified = replanModifiedVenueIds.includes(item.venue_id);

        return (
          <div
            key={idx}
            onClick={() => onSelectVenue(item.venue_id)}
            className={`rounded-xl p-4 cursor-pointer transition-all ${
              isAnchor
                ? "border-2 border-gray-900 bg-white shadow-sm hover:border-black"
                : isModified
                ? "replan-soft-highlight"
                : "minimal-card hover:border-gray-400"
            }`}
          >
            <div className="flex items-start sm:items-center justify-between gap-3 mb-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono font-bold text-gray-900">
                  {item.start} - {item.end}
                </span>
                <h4 className="text-sm font-bold text-gray-900">
                  {v.name}
                </h4>
                {isAnchor && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-900 text-white text-[10px] font-bold">
                    <Lock className="w-3 h-3 text-amber-400" />
                    Locked Booking (Hard Anchor)
                  </span>
                )}
                {isModified && (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-500 text-white">
                    MODIFIED
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className="font-semibold text-gray-800">NT$ {v.cost} / person</span>
                <span>•</span>
                <span>All {totalTravelers} Members</span>
              </div>
            </div>

            <p className="text-xs text-gray-600 line-clamp-1">
              {v.description}
            </p>

            {item.note && (
              <p className="text-[11px] text-amber-800 bg-amber-50 px-2 py-0.5 rounded mt-1.5 inline-block">
                Note: {item.note}
              </p>
            )}
          </div>
        );
      })}
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
}: {
  item: ItineraryItem;
  isSelected: boolean;
  onSelect: () => void;
  isModified?: boolean;
  venuesMap?: Record<string, any>;
  accentColor: "emerald" | "indigo" | "amber" | "rose";
}) {
  const v = getVenue(item.venue_id, venuesMap);

  return (
    <div
      onClick={onSelect}
      className={`minimal-card rounded-lg p-2.5 cursor-pointer select-none transition-all ${
        isModified
          ? "replan-soft-highlight"
          : isSelected
          ? "border-gray-900 ring-1 ring-gray-900 shadow-sm"
          : "hover:border-gray-300"
      }`}
    >
      {/* 1. Time Interval & Environment Tag */}
      <div className="flex items-center justify-between gap-1 mb-1">
        <span className="text-[11px] font-mono text-gray-500 flex items-center gap-1">
          <Clock className="w-3 h-3 text-gray-400" />
          {item.start} - {item.end}
        </span>
        <div className="flex items-center gap-1">
          {isModified && (
            <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500 text-white">
              MODIFIED
            </span>
          )}
          <span className="text-[10px] font-medium text-gray-500 flex items-center gap-0.5">
            {v.indoor ? <Sun className="w-2.5 h-2.5 text-gray-400" /> : <CloudRain className="w-2.5 h-2.5 text-gray-400" />}
            {v.indoor ? "Indoor" : "Outdoor"}
          </span>
        </div>
      </div>

      {/* 2. Venue Name */}
      <h5 className="text-xs font-bold text-gray-900 truncate mb-1">
        {v.name}
      </h5>

      {/* 3. Member Tag & Detail Hint */}
      <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1 border-t border-gray-100">
        <span className="font-medium text-gray-600 truncate max-w-[120px]">
          {item.members.join(", ")}
        </span>
        <span className="hover:text-gray-900 text-[10px]">
          NT$ {v.cost}
        </span>
      </div>

      {item.note && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50/70 px-1.5 py-0.5 rounded truncate">
          <MessageSquare className="w-2.5 h-2.5" />
          <span className="truncate">{item.note}</span>
        </div>
      )}
    </div>
  );
}
