"use client";

import React from "react";
import { Check, Loader2, AlertCircle, RotateCcw, ArrowLeft } from "lucide-react";
import { AgentStepEvent } from "../types";

interface CleanStepperProps {
  currentEvent: AgentStepEvent | null;
  errorMessage?: string | null;
  onRetry?: () => void;
  onReset?: () => void;
}

const STEPS = [
  { id: "orchestrator", label: "Analyze Preferences" },
  { id: "base_planner", label: "Split Sub-routes" },
  { id: "group_sync", label: "Align Convergence" },
  { id: "checker", label: "Rule Verification" },
];

export default function CleanStepper({
  currentEvent,
  errorMessage,
  onRetry,
  onReset,
}: CleanStepperProps) {
  const isError = Boolean(errorMessage || currentEvent?.event === "error");
  const displayError = errorMessage || (currentEvent?.event === "error" ? currentEvent.message : null);
  const activeNode = currentEvent?.node || "orchestrator";

  const getStepStatus = (stepId: string, index: number) => {
    const nodeOrder = ["orchestrator", "base_planner", "group_sync", "checker", "finished"];
    const currentIndex = nodeOrder.indexOf(activeNode);
    const targetIndex = nodeOrder.indexOf(stepId);

    if (currentEvent?.event === "finished" || currentIndex > targetIndex) {
      return "completed";
    }
    if (currentIndex === targetIndex) {
      return isError ? "error" : "active";
    }
    return "pending";
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#F9FAFB] p-6 text-gray-900">
      <div className="w-full max-w-lg minimal-panel rounded-2xl p-8 space-y-6 text-center animate-in fade-in duration-200">
        {/* Animated Loading Spinner or Error Icon */}
        <div
          className={`w-12 h-12 rounded-2xl flex items-center justify-center mx-auto border transition-all ${
            isError
              ? "bg-rose-50 border-rose-200 text-rose-600"
              : "bg-gray-100 border-gray-200 text-gray-900"
          }`}
        >
          {isError ? (
            <AlertCircle className="w-6 h-6 text-rose-600" />
          ) : (
            <Loader2 className="w-6 h-6 animate-spin text-gray-800" />
          )}
        </div>

        {/* Heading & Live Status */}
        <div className="space-y-2">
          <h3 className="text-xl font-bold tracking-tight text-gray-900">
            {isError ? "Planning Interrupted" : "Synthesizing Collaborative Itinerary"}
          </h3>
          <p
            className={`text-xs font-mono max-w-md mx-auto truncate ${
              isError ? "text-rose-600" : "text-gray-500"
            }`}
          >
            {displayError || currentEvent?.message || "Running multi-agent constraint satisfaction..."}
          </p>
        </div>

        {/* Error Action Buttons */}
        {isError && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 space-y-3 animate-in fade-in">
            <p className="text-[11px] text-rose-700 leading-relaxed">
              {displayError || "An unexpected error occurred while contacting planning services."}
            </p>
            <div className="flex items-center justify-center gap-2 pt-1">
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="px-3.5 py-1.5 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-xs font-bold transition-all flex items-center gap-1.5 shadow-xs"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Retry Plan</span>
                </button>
              )}
              {onReset && (
                <button
                  type="button"
                  onClick={onReset}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-gray-100 text-gray-700 text-xs font-semibold border border-gray-200 transition-all flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Return Home</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* 4-Step Stepper Progress Bar */}
        <div className="pt-2">
          <div className="grid grid-cols-4 gap-2">
            {STEPS.map((step, idx) => {
              const status = getStepStatus(step.id, idx);
              return (
                <div key={step.id} className="space-y-2 flex flex-col items-center text-center">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all ${
                      status === "completed"
                        ? "bg-emerald-600 text-white"
                        : status === "error"
                        ? "bg-rose-600 text-white ring-4 ring-rose-100"
                        : status === "active"
                        ? "bg-gray-900 text-white ring-4 ring-gray-200"
                        : "bg-gray-100 text-gray-400 border border-gray-200"
                    }`}
                  >
                    {status === "completed" ? (
                      <Check className="w-3.5 h-3.5" />
                    ) : (
                      idx + 1
                    )}
                  </div>
                  <span
                    className={`text-[11px] leading-tight font-medium ${
                      status === "error"
                        ? "text-rose-600 font-bold"
                        : status === "active"
                        ? "text-gray-900 font-bold"
                        : status === "completed"
                        ? "text-gray-700"
                        : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
