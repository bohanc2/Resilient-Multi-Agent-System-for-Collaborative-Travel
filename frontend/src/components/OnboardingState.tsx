"use client";

import React from "react";
import { ArrowRight, SlidersHorizontal, Compass, Sparkles } from "lucide-react";

interface OnboardingStateProps {
  onLoadPreset: () => void;
  onOpenIntake: () => void;
  backendHealthy: boolean;
  dataMode: string;
}

export default function OnboardingState({
  onLoadPreset,
  onOpenIntake,
  backendHealthy,
  dataMode,
}: OnboardingStateProps) {
  const isLive = dataMode === "Live API Connected";

  return (
    <div className="min-h-screen flex flex-col bg-[#F9FAFB] text-gray-900">
      {/* Minimal Top Header */}
      <header className="w-full h-14 border-b border-gray-200 bg-white/90 backdrop-blur px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center text-white">
            <Compass className="w-4 h-4" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-gray-900">
            AuraTravel
          </span>
          <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200">
            v2.0
          </span>
        </div>

        {/* Live Status Pill */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-xs text-gray-600">
          <span
            className={`w-2 h-2 rounded-full ${
              !backendHealthy
                ? "bg-rose-500"
                : isLive
                ? "bg-emerald-500 animate-pulse"
                : "bg-amber-500"
            }`}
          />
          <span className="text-[11px] font-medium">
            {!backendHealthy ? "Backend Offline" : dataMode}
          </span>
        </div>
      </header>

      {/* Hero Onboarding Card */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-xl minimal-panel rounded-2xl p-8 sm:p-10 space-y-8 text-center animate-in fade-in duration-300">
          {/* Icon */}
          <div className="w-12 h-12 rounded-2xl bg-gray-100 border border-gray-200 text-gray-900 mx-auto flex items-center justify-center">
            <Compass className="w-6 h-6 text-gray-800" />
          </div>

          {/* Heading & Value Proposition */}
          <div className="space-y-3">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
              Multi-Agent Collaborative Travel
            </h2>
            <p className="text-sm sm:text-base text-gray-600 leading-relaxed max-w-lg mx-auto">
              Coordinates diverse traveler budgets, walking limits, and individual preferences into unified, synchronized group itineraries.
              Deterministic constraint solvers guarantee arrival convergence within 15 minutes with zero hallucination.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            {/* Primary CTA */}
            <button
              onClick={onLoadPreset}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gray-900 hover:bg-gray-800 active:scale-[0.98] text-white text-sm font-semibold transition-all shadow-sm flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4 text-gray-300" />
              <span>Try Demo: 2-Day Taipei Group Trip</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Secondary CTA */}
            <button
              onClick={onOpenIntake}
              className="w-full sm:w-auto px-5 py-3 rounded-xl bg-white hover:bg-gray-50 active:scale-[0.98] text-gray-700 text-sm font-semibold transition-all border border-gray-200 shadow-sm flex items-center justify-center gap-2"
            >
              <SlidersHorizontal className="w-4 h-4 text-gray-500" />
              <span>Custom Group Setup</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
