"use client";

import React from "react";
import { Compass, RotateCcw, ShieldCheck, SlidersHorizontal } from "lucide-react";

interface MinimalNavbarProps {
  city: string;
  backendHealthy: boolean;
  dataMode: string;
  onReset: () => void;
  onOpenIntake: () => void;
  onOpenAudit: () => void;
}

export default function MinimalNavbar({
  city,
  backendHealthy,
  dataMode,
  onReset,
  onOpenIntake,
  onOpenAudit,
}: MinimalNavbarProps) {
  const isLive = dataMode === "Live API Connected";

  return (
    <header className="sticky top-0 z-40 w-full h-14 bg-white/95 backdrop-blur border-b border-gray-200 px-6 flex items-center justify-between">
      {/* Left: Brand & Navigation Controls */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gray-900 flex items-center justify-center text-white">
            <Compass className="w-3.5 h-3.5" />
          </div>
          <span className="text-sm font-bold tracking-tight text-gray-900">
            AuraTravel
          </span>
        </div>

        <span className="text-gray-300">|</span>

        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          {city} 6-Pax Collaborative Tour
        </span>

        {/* Change / Reset Button */}
        <button
          onClick={onReset}
          className="ml-2 px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-gray-200 transition-colors flex items-center gap-1.5"
          title="Return to initial onboarding or select another script"
        >
          <RotateCcw className="w-3 h-3 text-gray-500" />
          <span>Switch Script / Reset</span>
        </button>

        {/* Custom Intake trigger */}
        <button
          onClick={onOpenIntake}
          className="hidden sm:flex px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-gray-200 transition-colors items-center gap-1.5"
          title="Edit travelers, budgets, and constraints"
        >
          <SlidersHorizontal className="w-3 h-3 text-gray-500" />
          <span>Edit Setup</span>
        </button>
      </div>

      {/* Right: Discrete Status Capsules */}
      <div className="flex items-center gap-2.5">
        {/* Connection Status Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-xs text-gray-600">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              !backendHealthy
                ? "bg-rose-500"
                : isLive
                ? "bg-emerald-500"
                : "bg-amber-500"
            }`}
          />
          <span className="text-[11px] font-medium text-gray-700">
            {!backendHealthy ? "Offline" : isLive ? "Live API" : "Snapshot Mode"}
          </span>
        </div>

        {/* Deterministic Audit Pill (Click to open Audit Modal) */}
        <button
          onClick={onOpenAudit}
          className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 hover:bg-emerald-100/80 border border-emerald-200 text-emerald-800 text-xs font-semibold transition-colors cursor-pointer"
          title="Click to view 0-violation mathematical audit details"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>0 Violations (Audit Details)</span>
        </button>
      </div>
    </header>
  );
}
