"use client";

import React from "react";
import { Check, Loader2 } from "lucide-react";
import { AgentStepEvent } from "../types";

interface CleanStepperProps {
  currentEvent: AgentStepEvent | null;
}

const STEPS = [
  { id: "orchestrator", label: "Analyze Preferences" },
  { id: "base_planner", label: "Split Sub-routes" },
  { id: "group_sync", label: "Align Convergence" },
  { id: "checker", label: "Rule Verification" },
];

export default function CleanStepper({ currentEvent }: CleanStepperProps) {
  const activeNode = currentEvent?.node || "orchestrator";

  const getStepStatus = (stepId: string, index: number) => {
    const nodeOrder = ["orchestrator", "base_planner", "group_sync", "checker", "finished"];
    const currentIndex = nodeOrder.indexOf(activeNode);
    const targetIndex = nodeOrder.indexOf(stepId);

    if (currentEvent?.event === "finished" || currentIndex > targetIndex) {
      return "completed";
    }
    if (currentIndex === targetIndex) {
      return "active";
    }
    return "pending";
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#F9FAFB] p-6 text-gray-900">
      <div className="w-full max-w-lg minimal-panel rounded-2xl p-8 space-y-6 text-center animate-in fade-in duration-200">
        {/* Animated Loading Spinner */}
        <div className="w-12 h-12 rounded-2xl bg-gray-100 border border-gray-200 flex items-center justify-center mx-auto text-gray-900">
          <Loader2 className="w-6 h-6 animate-spin text-gray-800" />
        </div>

        {/* Heading & Live Status */}
        <div className="space-y-2">
          <h3 className="text-xl font-bold tracking-tight text-gray-900">
            Synthesizing Collaborative Itinerary
          </h3>
          <p className="text-xs text-gray-500 font-mono max-w-md mx-auto truncate">
            {currentEvent?.message || "Running multi-agent constraint satisfaction..."}
          </p>
        </div>

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
                      status === "active"
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
