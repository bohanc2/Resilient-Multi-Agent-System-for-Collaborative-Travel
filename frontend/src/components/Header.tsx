"use client";

import React from "react";
import { Sparkles, SlidersHorizontal, ShieldCheck, Activity, Compass } from "lucide-react";

interface HeaderProps {
  onLoadPreset: () => void;
  onOpenIntake: () => void;
  onToggleAudit: () => void;
  backendHealthy: boolean;
  dataMode?: string;
  isStreaming: boolean;
  replanActive: boolean;
}

export default function Header({
  onLoadPreset,
  onOpenIntake,
  onToggleAudit,
  backendHealthy,
  dataMode = "Live API Connected",
  isStreaming,
  replanActive,
}: HeaderProps) {
  const isLive = dataMode === "Live API Connected";
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/10 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
      {/* Brand & Badge */}
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/25 ring-1 ring-white/20">
          <Compass className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              AuraTravel
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Multi-Agent v2.0
              </span>
            </h1>
          </div>
          <p className="text-xs text-slate-400">
            Resilient Collaborative Travel Planning Engine
          </p>
        </div>
      </div>

      {/* Center Status Indicators */}
      <div className="hidden lg:flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-slate-700/60 text-xs text-slate-300">
          <span
            className={`w-2 h-2 rounded-full ${
              !backendHealthy
                ? "bg-rose-500"
                : isLive
                ? "bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400"
                : "bg-amber-400"
            }`}
          />
          <span className="font-medium">
            {!backendHealthy ? "Backend Offline" : dataMode}
          </span>
        </div>

        {replanActive && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-xs font-medium text-amber-300 animate-pulse">
            <Activity className="w-3.5 h-3.5" />
            <span>Contingency Active</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2.5">
        {/* Load Preset Demo Button */}
        <button
          onClick={onLoadPreset}
          disabled={isStreaming}
          className="relative group overflow-hidden px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 text-white font-medium text-xs sm:text-sm shadow-md shadow-sky-500/20 hover:shadow-sky-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4 text-sky-200" />
          <span>載入台北 6 人協作展示劇本</span>
        </button>

        {/* Multiplayer Intake Button */}
        <button
          onClick={onOpenIntake}
          disabled={isStreaming}
          className="px-3.5 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 border border-slate-700/80 hover:border-slate-600 text-xs sm:text-sm font-medium transition-all flex items-center gap-2 disabled:opacity-50"
        >
          <SlidersHorizontal className="w-4 h-4 text-slate-400" />
          <span className="hidden sm:inline">自訂多人偏好</span>
        </button>

        {/* Audit Drawer Toggle */}
        <button
          onClick={onToggleAudit}
          className="px-3.5 py-2 rounded-xl bg-emerald-950/30 hover:bg-emerald-900/40 text-emerald-300 border border-emerald-500/30 hover:border-emerald-500/50 text-xs sm:text-sm font-medium transition-all flex items-center gap-1.5"
          title="檢視確定性審計報告"
        >
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="hidden md:inline">審計驗證</span>
        </button>
      </div>
    </header>
  );
}
