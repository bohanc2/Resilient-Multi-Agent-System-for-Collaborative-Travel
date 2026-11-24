"use client";

import React from "react";
import { CloudLightning, RotateCcw, Loader2 } from "lucide-react";

interface DisruptionSimulatorProps {
  onTriggerRainSpike: () => void;
  onResetReplan: () => void;
  isReplanActive: boolean;
  isLoading: boolean;
  disabled: boolean;
}

export default function DisruptionSimulator({
  onTriggerRainSpike,
  onResetReplan,
  isReplanActive,
  isLoading,
  disabled,
}: DisruptionSimulatorProps) {
  return (
    <div className="absolute top-4 right-4 z-[400] w-64 minimal-panel rounded-xl p-3.5 shadow-md border border-gray-200 bg-white/95 backdrop-blur space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-gray-900 tracking-tight">
          Scenario Simulation
        </span>
        <span
          className={`w-2 h-2 rounded-full ${
            isReplanActive ? "bg-amber-500 animate-pulse" : "bg-emerald-500"
          }`}
        />
      </div>

      <p className="text-[11px] text-gray-500 leading-snug">
        Test dynamic contingency: localizes weather impact without moving unaffected tracks or dinner.
      </p>

      {/* Single Toggle Action Button */}
      {isReplanActive ? (
        <button
          onClick={onResetReplan}
          disabled={disabled || isLoading}
          className="w-full py-2 px-3 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold transition-all border border-gray-200 flex items-center justify-center gap-1.5 active:scale-[0.98]"
        >
          <RotateCcw className="w-3.5 h-3.5 text-gray-600" />
          <span>Revert to Sunny Plan</span>
        </button>
      ) : (
        <button
          onClick={onTriggerRainSpike}
          disabled={disabled || isLoading}
          className="w-full py-2 px-3 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold transition-all shadow-xs flex items-center justify-center gap-1.5 active:scale-[0.98] disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <CloudLightning className="w-3.5 h-3.5 text-amber-400" />
          )}
          <span>{isLoading ? "Replanning..." : "Simulate 14:00 Rain Spike"}</span>
        </button>
      )}
    </div>
  );
}
