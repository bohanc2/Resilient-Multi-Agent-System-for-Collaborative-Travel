"use client";

import React, { useState } from "react";
import { X, Users, Lock, Sparkles } from "lucide-react";
import { Setup, Traveler } from "../types";

interface IntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  setup: Setup;
  onSubmit: (newSetup: Setup) => void;
  isStreaming: boolean;
}

const CITY_DEFAULTS: Record<
  string,
  { hotel: string; dinnerVenue: string; dinnerName: string; currency: string; defaultBudget: number }
> = {
  taipei: {
    hotel: "hotel_ximen",
    dinnerVenue: "din_tai_fung_101",
    dinnerName: "Din Tai Fung (Taipei 101)",
    currency: "TWD",
    defaultBudget: 2000,
  },
  paris: {
    hotel: "par_hotel",
    dinnerVenue: "par_chartier",
    dinnerName: "Bouillon Chartier (Paris)",
    currency: "EUR",
    defaultBudget: 150,
  },
  tokyo: {
    hotel: "tky_hotel",
    dinnerVenue: "tky_gonpachi",
    dinnerName: "Gonpachi Nishi-Azabu (Tokyo)",
    currency: "JPY",
    defaultBudget: 16000,
  },
  nyc: {
    hotel: "nyc_hotel",
    dinnerVenue: "nyc_katz",
    dinnerName: "Katz's Delicatessen (NYC)",
    currency: "USD",
    defaultBudget: 160,
  },
  seattle: {
    hotel: "sea_hotel",
    dinnerVenue: "sea_ivars",
    dinnerName: "Ivar's Acres of Clams (Seattle)",
    currency: "USD",
    defaultBudget: 160,
  },
};

export default function IntakeModal({
  isOpen,
  onClose,
  setup,
  onSubmit,
  isStreaming,
}: IntakeModalProps) {
  const [currentSetup, setCurrentSetup] = useState<Setup>(setup);

  if (!isOpen) return null;

  const handleCityChange = (cityName: string) => {
    const normalized = cityName.toLowerCase().trim();
    const cityConfig = CITY_DEFAULTS[normalized];
    const newHotel = cityConfig ? cityConfig.hotel : `${normalized}_hotel`;
    const newDinnerVenue = cityConfig ? cityConfig.dinnerVenue : "";

    const updatedAnchors = currentSetup.anchors.map((a) => ({
      ...a,
      venue_id: newDinnerVenue,
    }));

    const updatedTravelers = currentSetup.travelers.map((t) => ({
      ...t,
      budget: cityConfig ? cityConfig.defaultBudget : t.budget,
    }));

    setCurrentSetup({
      ...currentSetup,
      city: normalized,
      start_location: newHotel,
      travelers: updatedTravelers,
      anchors: updatedAnchors,
    });
  };

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-2xl border border-gray-200 p-6 space-y-5 shadow-xl animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gray-100 text-gray-800 flex items-center justify-center border border-gray-200">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900">Multiplayer Intake & Constraints</h3>
              <p className="text-xs text-gray-500">Configure traveler budgets, walking effort, and immutable anchors</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Destination City Section */}
          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                Destination City (OSM & Google Places Search)
              </label>
              <span className="text-[11px] text-gray-700 font-mono font-semibold">
                {currentSetup.city.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={currentSetup.city}
                onChange={(e) => handleCityChange(e.target.value)}
                placeholder="Enter city name (e.g. taipei, paris, tokyo, nyc, seattle...)"
                className="flex-1 px-3 py-1.5 rounded-lg bg-white text-gray-900 border border-gray-300 text-xs focus:outline-none focus:border-gray-900"
              />
              <div className="flex items-center gap-1">
                {["taipei", "paris", "tokyo", "nyc", "seattle"].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => handleCityChange(c)}
                    className={`px-2 py-1 rounded text-[11px] font-medium transition-all ${
                      currentSetup.city.toLowerCase() === c
                        ? "bg-gray-900 text-white"
                        : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Travelers Grid */}
          <div className="space-y-2.5">
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
              Traveler Profiles ({currentSetup.travelers.length} Members)
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {currentSetup.travelers.map((t, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-gray-50 border border-gray-200 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gray-900">{t.name}</span>
                    <span className="text-[10px] text-gray-400">Traveler #{idx + 1}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-0.5">
                        Budget ({CITY_DEFAULTS[currentSetup.city.toLowerCase()]?.currency || "Local"})
                      </label>
                      <input
                        type="number"
                        value={t.budget}
                        onChange={(e) => handleTravelerChange(idx, "budget", Number(e.target.value))}
                        className="w-full px-2 py-1 rounded bg-white text-gray-900 border border-gray-300 text-xs focus:outline-none focus:border-gray-900"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-0.5">Walk Limit (0-3)</label>
                      <select
                        value={t.max_walk}
                        onChange={(e) => handleTravelerChange(idx, "max_walk", Number(e.target.value))}
                        className="w-full px-2 py-1 rounded bg-white text-gray-900 border border-gray-300 text-xs focus:outline-none focus:border-gray-900"
                      >
                        <option value={0}>Lv.0 (Flat / Seated)</option>
                        <option value={1}>Lv.1 (Light Walk)</option>
                        <option value={2}>Lv.2 (Stairs / Trails)</option>
                        <option value={3}>Lv.3 (Challenging Hike)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-gray-500 block mb-0.5">Interests (comma separated)</label>
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
                      className="w-full px-2 py-1 rounded bg-white text-gray-900 border border-gray-300 text-xs focus:outline-none focus:border-gray-900"
                      placeholder="e.g. hiking, scenic, cafe, art"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hard Anchor Section */}
          <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 space-y-1.5">
            <div className="flex items-center gap-1.5 text-amber-900 font-semibold text-xs">
              <Lock className="w-3.5 h-3.5 text-amber-600" />
              <span>Locked Booking (Hard Anchor - Dinner Block)</span>
            </div>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              Fixed 18:30 - 19:30 {CITY_DEFAULTS[currentSetup.city.toLowerCase()]?.dinnerName || "City Center Dining Landmark"}, all {currentSetup.travelers.length} members attending. Multi-agent solver guarantees arrival convergence ≤ 15 min.
            </p>
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-white hover:bg-gray-100 text-gray-700 text-xs font-semibold border border-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isStreaming}
              className="px-5 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-xs font-bold shadow-sm active:scale-[0.98] transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Save & Stream Plan</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
