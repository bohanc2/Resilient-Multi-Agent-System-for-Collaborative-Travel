"use client";

import React from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, ShieldCheck, X } from "lucide-react";
import { ReplanDiff } from "../types";

interface ReplanDiffBannerProps {
  diff: ReplanDiff | null;
  onDismiss: () => void;
}

export default function ReplanDiffBanner({ diff, onDismiss }: ReplanDiffBannerProps) {
  if (!diff) return null;

  return (
    <div className="w-full glass-panel border-b border-amber-500/30 bg-gradient-to-r from-amber-950/40 via-slate-900/80 to-slate-950/80 p-4 transition-all animate-in slide-in-from-top duration-300">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Left: Summary */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-semibold">
              <AlertTriangle className="w-3.5 h-3.5" />
              14:00 突發氣候應變成功
            </span>
            <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              18:30 晚餐鎖定 100% 保留
            </span>
          </div>
          <p className="text-sm font-medium text-slate-200">
            {diff.event_summary}
          </p>
        </div>

        {/* Center: Replaced Details Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {diff.modified_groups.map((mod, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-amber-500/30 text-slate-300"
            >
              <span className="font-semibold text-emerald-400">
                {mod.members.join(", ")}:
              </span>
              <span className="line-through text-slate-500">
                {mod.original_item.name} ({mod.original_item.start} - {mod.original_item.end})
              </span>
              <ArrowRight className="w-3 h-3 text-amber-400 shrink-0" />
              <span className="font-medium text-amber-300">
                {mod.new_item.name} ({mod.new_item.start} - {mod.new_item.end})
              </span>
            </div>
          ))}

          <div className="px-2.5 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{diff.unaffected_count} 個時段原封不動</span>
          </div>
        </div>

        {/* Dismiss Button */}
        <button
          onClick={onDismiss}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors shrink-0"
          title="關閉提示"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
