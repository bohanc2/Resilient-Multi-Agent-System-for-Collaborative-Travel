"use client";

import React, { useState } from "react";
import { X, Users, Lock, Sparkles, Plus, Trash2 } from "lucide-react";
import { Setup, Traveler } from "../types";

interface IntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  setup: Setup;
  onSubmit: (newSetup: Setup) => void;
  isStreaming: boolean;
}

export default function IntakeModal({
  isOpen,
  onClose,
  setup,
  onSubmit,
  isStreaming,
}: IntakeModalProps) {
  const [currentSetup, setCurrentSetup] = useState<Setup>(setup);

  if (!isOpen) return null;

  const handleTravelerChange = (index: number, field: keyof Traveler, value: any) => {
    const updated = [...currentSetup.travelers];
    updated[index] = { ...updated[index], [field]: value };
    setCurrentSetup({ ...currentSetup, travelers: updated });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(currentSetup);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-3xl rounded-2xl border border-white/10 p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-500/20 text-sky-400">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Multiplayer Intake & Hard Anchors</h3>
              <p className="text-xs text-slate-400">Configure traveler budgets, walking limits, interest tags, and immutable hard anchors</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Destination City Section */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Destination City (Global Real Venue Search via OpenStreetMap & Google Places)
              </label>
              <span className="text-[11px] text-sky-400 font-mono">
                {currentSetup.city.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={currentSetup.city}
                onChange={(e) => setCurrentSetup({ ...currentSetup, city: e.target.value.toLowerCase() })}
                placeholder="Enter city name (e.g. taipei, tokyo, kyoto, paris, seattle, new york...)"
                className="flex-1 px-3 py-1.5 rounded-lg bg-slate-800 text-white border border-slate-700 text-xs focus:outline-none focus:border-sky-500"
              />
              <div className="flex items-center gap-1">
                {["taipei", "kyoto", "tokyo", "paris"].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCurrentSetup({ ...currentSetup, city: c })}
                    className={`px-2 py-1 rounded text-[11px] font-medium transition-all ${
                      currentSetup.city.toLowerCase() === c
                        ? "bg-sky-500/30 text-sky-300 border border-sky-500/50"
                        : "bg-slate-800 text-slate-400 hover:text-white"
                    }`}
                  >
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Travelers Grid */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <span>Traveler Profiles ({currentSetup.travelers.length} Members)</span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {currentSetup.travelers.map((t, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">{t.name}</span>
                    <span className="text-[11px] text-slate-400">Traveler #{idx + 1}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Budget Limit (TWD)</label>
                      <input
                        type="number"
                        value={t.budget}
                        onChange={(e) => handleTravelerChange(idx, "budget", Number(e.target.value))}
                        className="w-full px-2.5 py-1 rounded-lg bg-slate-800 text-white border border-slate-700 text-xs focus:outline-none focus:border-sky-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-0.5">Walk Limit (Lv.0~3)</label>
                      <select
                        value={t.max_walk}
                        onChange={(e) => handleTravelerChange(idx, "max_walk", Number(e.target.value))}
                        className="w-full px-2 py-1 rounded-lg bg-slate-800 text-white border border-slate-700 text-xs focus:outline-none focus:border-sky-500"
                      >
                        <option value={0}>Lv.0 (Flat / Seated)</option>
                        <option value={1}>Lv.1 (Light Walk)</option>
                        <option value={2}>Lv.2 (Stairs / Trails)</option>
                        <option value={3}>Lv.3 (Challenging Hike)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 block mb-0.5">Interest Tags (comma separated)</label>
                    <input
                      type="text"
                      value={t.interests.join(", ")}
                      onChange={(e) =>
                        handleTravelerChange(
                          idx,
                          "interests",
                          e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                        )
                      }
                      className="w-full px-2.5 py-1 rounded-lg bg-slate-800 text-white border border-slate-700 text-xs focus:outline-none focus:border-sky-500"
                      placeholder="e.g. hiking, scenic, cafe, art"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hard Anchor Section */}
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-400" />
              <h4 className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                Locked Booking (Hard Anchor - Dinner Block)
              </h4>
            </div>
            <p className="text-xs text-slate-300">
              Fixed 18:30 - 19:30 Din Tai Fung (Taipei 101), all 6 members attending. Multi-agent solver guarantees all split tracks converge at or before 18:15.
            </p>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-3 pt-2 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs sm:text-sm font-medium transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isStreaming}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs sm:text-sm font-bold shadow-lg shadow-sky-500/20 active:scale-[0.98] transition-all flex items-center gap-1.5"
            >
              <Sparkles className="w-4 h-4" />
              <span>Save & Stream Plan</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
