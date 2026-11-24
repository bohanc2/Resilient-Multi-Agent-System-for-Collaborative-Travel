"use client";

import React, { useState } from "react";
import { X, Plus, Clock, DollarSign, MapPin, Tag } from "lucide-react";
import { Traveler } from "../types";

interface AddCustomStopModalProps {
  isOpen: boolean;
  onClose: () => void;
  travelers: Traveler[];
  onAddStop: (data: {
    name: string;
    start: string;
    end: string;
    cost: number;
    indoor: boolean;
    members: string[];
    note?: string;
  }) => void;
}

const TIME_OPTIONS = (() => {
  const options: { value: string; label: string }[] = [];
  for (let h = 7; h <= 23; h++) {
    for (let m = 0; m < 60; m += 15) {
      const hh = String(h).padStart(2, "0");
      const mm = String(m).padStart(2, "0");
      const value = `${hh}:${mm}`;
      const period = h >= 12 ? "PM" : "AM";
      const displayH = h % 12 === 0 ? 12 : h % 12;
      const label = `${String(displayH).padStart(2, "0")}:${mm} ${period}`;
      options.push({ value, label });
    }
  }
  return options;
})();

export default function AddCustomStopModal({
  isOpen,
  onClose,
  travelers,
  onAddStop,
}: AddCustomStopModalProps) {
  const [name, setName] = useState("");
  const [start, setStart] = useState("14:00");
  const [end, setEnd] = useState("15:30");
  const [cost, setCost] = useState(0);
  const [indoor, setIndoor] = useState(true);
  const [selectedMembers, setSelectedMembers] = useState<string[]>(
    travelers.map((t) => t.name)
  );
  const [note, setNote] = useState("");

  if (!isOpen) return null;

  const toggleMember = (mName: string) => {
    if (selectedMembers.includes(mName)) {
      if (selectedMembers.length > 1) {
        setSelectedMembers(selectedMembers.filter((m) => m !== mName));
      }
    } else {
      setSelectedMembers([...selectedMembers, mName]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    onAddStop({
      name: name.trim(),
      start,
      end,
      cost: Number(cost) || 0,
      indoor,
      members: selectedMembers,
      note: note.trim() || undefined,
    });

    // Reset form
    setName("");
    setStart("14:00");
    setEnd("15:30");
    setCost(0);
    setNote("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 p-6 space-y-5 shadow-xl animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gray-900 text-white flex items-center justify-center">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900">Add Custom Stop</h3>
              <p className="text-xs text-gray-500">Insert custom activity or reservation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Venue Name */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-700">Stop Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Elephant Mountain Viewpoint, Boba Tea..."
              className="w-full px-3 py-2 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
            />
          </div>

          {/* Time Interval */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700">Start Time</label>
              <select
                required
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900 cursor-pointer"
              >
                {!TIME_OPTIONS.some((o) => o.value === start) && start && (
                  <option value={start}>{start}</option>
                )}
                {TIME_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700">End Time</label>
              <select
                required
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900 cursor-pointer"
              >
                {!TIME_OPTIONS.some((o) => o.value === end) && end && (
                  <option value={end}>{end}</option>
                )}
                {TIME_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Cost & Environment */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700">Cost / Person</label>
              <input
                type="number"
                min={0}
                value={cost}
                onChange={(e) => setCost(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700">Setting</label>
              <button
                type="button"
                onClick={() => setIndoor(!indoor)}
                className={`w-full px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  indoor
                    ? "bg-sky-50 text-sky-700 border-sky-200"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                }`}
              >
                {indoor ? "Indoor Venue" : "Outdoor Activity"}
              </button>
            </div>
          </div>

          {/* Attending Members */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-700">Attending Members</label>
            <div className="flex flex-wrap gap-1.5">
              {travelers.map((t) => {
                const active = selectedMembers.includes(t.name);
                return (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => toggleMember(t.name)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                      active
                        ? "bg-gray-900 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {t.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Personal Note */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-700">Personal Notes (Optional)</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Need reservation or comfortable shoes"
              className="w-full px-3 py-2 rounded-lg bg-white border border-gray-300 text-xs text-gray-900 focus:outline-none focus:border-gray-900"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-white hover:bg-gray-100 text-gray-700 text-xs font-semibold border border-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-xs font-bold shadow-sm transition-all active:scale-[0.98]"
            >
              Add to Itinerary
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
