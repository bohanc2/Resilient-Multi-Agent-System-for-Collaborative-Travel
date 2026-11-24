"use client";

import React from "react";
import { CheckCircle2, CircleDashed, Cpu, GitCommit, Layers, ShieldCheck } from "lucide-react";
import { AgentStepEvent } from "../types";

interface AgentStatusBarProps {
  currentEvent: AgentStepEvent | null;
  isStreaming: boolean;
}

const NODES = [
  { id: "orchestrator", label: "Orchestrator", icon: Cpu },
  { id: "base_planner", label: "Base Planner", icon: Layers },
  { id: "group_sync", label: "Group Sync", icon: GitCommit },
  { id: "checker", label: "Deterministic Checker", icon: ShieldCheck },
  { id: "finished", label: "Verified & Complete", icon: CheckCircle2 },
];

export default function AgentStatusBar({ currentEvent, isStreaming }: AgentStatusBarProps) {
  if (!currentEvent && !isStreaming) return null;

  const currentNodeId = currentEvent?.node || (currentEvent?.event === "finished" ? "finished" : "orchestrator");
  const currentIndex = NODES.findIndex((n) => n.id === currentNodeId);

  return (
    <div className="w-full glass-panel border-b border-white/10 px-6 py-2.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        {/* Reasoning Steps Capsule */}
        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto w-full md:w-auto py-1">
          {NODES.map((node, index) => {
            const Icon = node.icon;
            const isCompleted = currentIndex > index || currentEvent?.event === "finished";
            const isActive = currentIndex === index && currentEvent?.event !== "finished";

            return (
              <React.Fragment key={node.id}>
                <div
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    isCompleted
                      ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                      : isActive
                      ? "bg-sky-500/20 text-sky-200 border border-sky-400/50 shadow-sm shadow-sky-500/30 animate-pulse"
                      : "bg-slate-900/40 text-slate-500 border border-slate-800"
                  }`}
                >
                  {isActive ? (
                    <CircleDashed className="w-3.5 h-3.5 animate-spin text-sky-400" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                  <span className="whitespace-nowrap">{node.label}</span>
                </div>
                {index < NODES.length - 1 && (
                  <div
                    className={`w-3 h-0.5 rounded-full ${
                      currentIndex > index ? "bg-emerald-500/50" : "bg-slate-800"
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Live Step Message */}
        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-950/60 px-3 py-1 rounded-lg border border-white/5 truncate max-w-xl">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping shrink-0" />
          <span className="text-slate-400 shrink-0">Status:</span>
          <span className="truncate">{currentEvent?.message || "Multi-agent engine standing by..."}</span>
        </div>
      </div>
    </div>
  );
}
