"use client";

import React from "react";
import { CloudLightning, RefreshCw, Zap, ShieldAlert, CheckCircle2 } from "lucide-react";

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
    <div className="glass-panel p-4 rounded-2xl border border-white/10 shadow-2xl space-y-3">
      {/* Title & Badge */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-300">
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-white">
            Disruption Simulator (Event Injector)
          </h4>
        </div>

        {isReplanActive ? (
          <span className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
            <CheckCircle2 className="w-3 h-3" />
            Active Contingency
          </span>
        ) : (
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
            Standby Ready
          </span>
        )}
      </div>

      <p className="text-xs text-slate-300 leading-relaxed">
        Simulate an abrupt 14:00 weather shock (85% rain spike) to test how Multi-Agent executes localized replanning, replacing only the outdoor hiking track with an indoor alternative <strong>without altering other tracks or the 18:30 dinner anchor</strong>.
      </p>

      {/* Trigger Buttons */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={onTriggerRainSpike}
          disabled={disabled || isLoading || isReplanActive}
          className="flex-1 py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-slate-950 font-bold text-xs sm:text-sm shadow-lg shadow-amber-500/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
          ) : (
            <CloudLightning className="w-4 h-4 text-slate-950" />
          )}
          <span>{isLoading ? "Calculating Contingency..." : "Simulate 14:00 Rain Spike (85%)"}</span>
        </button>

        {isReplanActive && (
          <button
            onClick={onResetReplan}
            className="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition-all"
            title="Reset to Original Plan"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
