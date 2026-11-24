"use client";

import React from "react";
import { CheckCircle2, ShieldCheck, X } from "lucide-react";
import { ReplanDiff } from "../types";

interface ReplanDiffBannerProps {
  diff: ReplanDiff | null;
  onDismiss: () => void;
}

export default function ReplanDiffBanner({ diff, onDismiss }: ReplanDiffBannerProps) {
  if (!diff) return null;

  return (
    <div className="w-full bg-amber-50/90 border border-amber-200/80 rounded-xl px-4 py-2.5 flex items-center justify-between gap-3 text-xs text-amber-900 animate-in fade-in duration-200 shadow-xs">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4 text-amber-600 shrink-0" />
        <span className="font-semibold">
          Localized Replan:
        </span>
        <span className="text-amber-800">
          Hiking afternoon venue replaced with Huashan Creative Park (Indoor). Remaining tracks and 18:30 dinner anchor 100% retained.
        </span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-600" />
          {diff.unaffected_count} Unaffected
        </span>
        <button
          onClick={onDismiss}
          className="text-amber-600 hover:text-amber-900 p-1 rounded hover:bg-amber-100 transition-colors"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
