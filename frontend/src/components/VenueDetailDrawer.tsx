"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Clock,
  DollarSign,
  Footprints,
  Sun,
  CloudRain,
  Edit3,
  Check,
  Lock,
} from "lucide-react";
import { VenueInfo, ItineraryItem } from "../types";

interface VenueDetailDrawerProps {
  isOpen: boolean;
  venue: VenueInfo | null;
  item?: ItineraryItem | null;
  isAnchor?: boolean;
  onClose: () => void;
  onUpdateItem?: (
    venueId: string,
    updates: { name: string; start: string; end: string; note?: string }
  ) => void;
}

export default function VenueDetailDrawer({
  isOpen,
  venue,
  item,
  isAnchor = false,
  onClose,
  onUpdateItem,
}: VenueDetailDrawerProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editStart, setEditStart] = useState("");
  const [editEnd, setEditEnd] = useState("");
  const [editNote, setEditNote] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (venue) {
      setEditName(venue.name || "");
    }
    if (item) {
      setEditStart(item.start || "09:00");
      setEditEnd(item.end || "10:30");
      setEditNote(item.note || "");
    }
    setIsEditing(false);
    setSaveSuccess(false);
  }, [venue, item]);

  if (!isOpen || !venue) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!onUpdateItem || !item) return;

    onUpdateItem(item.venue_id, {
      name: editName.trim() || venue.name,
      start: editStart,
      end: editEnd,
      note: editNote.trim() || undefined,
    });

    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      setIsEditing(false);
    }, 800);
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-[2px] animate-in fade-in duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm h-full bg-white border-l border-gray-200 p-6 flex flex-col justify-between shadow-xl animate-in slide-in-from-right duration-200 overflow-y-auto"
      >
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-gray-100">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[11px] font-mono font-semibold uppercase text-gray-400">
                  Venue Details
                </span>
                {isAnchor && (
                  <span className="flex items-center gap-1 px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[10px] font-bold">
                    <Lock className="w-2.5 h-2.5" />
                    Locked
                  </span>
                )}
              </div>
              <h3 className="text-lg font-bold text-gray-900 tracking-tight">
                {editName || venue.name}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Key Attributes Grid */}
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            <div className="p-2.5 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 flex items-center gap-1">
                <DollarSign className="w-3.5 h-3.5 text-gray-600" /> Cost / Person
              </span>
              <span className="text-sm font-bold text-gray-900">
                NT$ {venue.cost}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 flex items-center gap-1">
                <Footprints className="w-3.5 h-3.5 text-gray-600" /> Walk Effort
              </span>
              <span className="text-sm font-bold text-gray-900">
                Lv. {venue.walk}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-gray-600" /> Scheduled
              </span>
              <span className="text-xs font-semibold text-gray-800">
                {item ? `${item.start} - ${item.end}` : `${venue.open} - ${venue.close}`}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 flex items-center gap-1">
                {venue.indoor ? (
                  <Sun className="w-3.5 h-3.5 text-sky-600" />
                ) : (
                  <CloudRain className="w-3.5 h-3.5 text-emerald-600" />
                )}
                Setting
              </span>
              <span className="text-xs font-semibold text-gray-800">
                {venue.indoor ? "Indoor" : "Outdoor"}
              </span>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
              Overview
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-2.5 rounded-xl border border-gray-100">
              {venue.description || "Curated point of interest selected based on group profile matching."}
            </p>
          </div>

          {/* Category Tags */}
          {venue.tags && venue.tags.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                Tags
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {venue.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 text-[11px] font-medium"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Personal Note if exists */}
          {item?.note && !isEditing && (
            <div className="p-2.5 rounded-xl bg-amber-50/60 border border-amber-200 text-xs text-amber-900 space-y-1">
              <span className="font-semibold block text-[11px]">Personal Note:</span>
              <p className="text-xs text-amber-800">{item.note}</p>
            </div>
          )}

          {/* Interactive Editing Section (For non-locked items) */}
          {item && !isAnchor && (
            <div className="pt-3 border-t border-gray-100 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-800 uppercase tracking-wide flex items-center gap-1.5">
                  <Edit3 className="w-3.5 h-3.5 text-gray-600" />
                  <span>Interactive Edit</span>
                </span>
                {!isEditing && (
                  <button
                    type="button"
                    onClick={() => setIsEditing(true)}
                    className="text-xs text-gray-700 font-semibold hover:text-black hover:underline"
                  >
                    Edit Activity
                  </button>
                )}
              </div>

              {isEditing ? (
                <form onSubmit={handleSave} className="space-y-3 bg-gray-50 p-3 rounded-xl border border-gray-200">
                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-gray-600">Venue Name</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-gray-600">Start Time</label>
                      <input
                        type="time"
                        value={editStart}
                        onChange={(e) => setEditStart(e.target.value)}
                        className="w-full px-2 py-1 rounded bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-gray-600">End Time</label>
                      <input
                        type="time"
                        value={editEnd}
                        onChange={(e) => setEditEnd(e.target.value)}
                        className="w-full px-2 py-1 rounded bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-semibold text-gray-600">Personal Note</label>
                    <input
                      type="text"
                      value={editNote}
                      onChange={(e) => setEditNote(e.target.value)}
                      placeholder="Add personal note..."
                      className="w-full px-2.5 py-1.5 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1 rounded-lg bg-white border border-gray-200 text-xs text-gray-600 hover:bg-gray-100"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-3.5 py-1 rounded-lg bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 flex items-center gap-1 shadow-sm"
                    >
                      {saveSuccess ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Saved!</span>
                        </>
                      ) : (
                        <span>Save Changes</span>
                      )}
                    </button>
                  </div>
                </form>
              ) : (
                <p className="text-[11px] text-gray-500">
                  Click Edit Activity to customize venue name, schedule, or notes. Changes update the multi-track timeline immediately.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-100 text-right mt-4">
          <button
            onClick={onClose}
            className="w-full py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
}
