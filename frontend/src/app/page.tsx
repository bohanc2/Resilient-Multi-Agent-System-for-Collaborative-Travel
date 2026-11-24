"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import OnboardingState from "../components/OnboardingState";
import CleanStepper from "../components/CleanStepper";
import MinimalNavbar from "../components/MinimalNavbar";
import ReplanDiffBanner from "../components/ReplanDiffBanner";
import SwimlaneTimeline from "../components/SwimlaneTimeline";
import DisruptionSimulator from "../components/DisruptionSimulator";
import AuditDrawer from "../components/AuditDrawer";
import IntakeModal from "../components/IntakeModal";
import VenueDetailDrawer from "../components/VenueDetailDrawer";
import AddCustomStopModal from "../components/AddCustomStopModal";
import { AgentStepEvent, ItineraryItem, PlanOutput, ReplanDiff, Setup, Traveler } from "../types";
import { getVenue } from "../lib/venues";

// Dynamic import for Leaflet map to avoid window undefined SSR error
const InteractiveMap = dynamic(() => import("../components/InteractiveMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[550px] rounded-xl border border-gray-200 bg-white flex flex-col items-center justify-center text-gray-400 gap-2">
      <div className="w-7 h-7 rounded-full border-2 border-gray-900 border-t-transparent animate-spin" />
      <span className="text-xs text-gray-500 font-medium">Loading interactive map...</span>
    </div>
  ),
});

const DEFAULT_SETUP: Setup = {
  city: "taipei",
  days: 2,
  duration_days: 2,
  weekday: "Sat",
  day_start: "09:30",
  day_end: "21:00",
  start_location: "hotel_ximen",
  travelers: [
    { name: "Traveler 1", interests: ["hiking", "scenic"], max_walk: 2, budget: 2000 },
    { name: "Traveler 2", interests: ["food", "cafe"], max_walk: 1, budget: 1800 },
  ],
  anchors: [
    {
      venue_id: "din_tai_fung_101",
      start: "18:30",
      end: "20:00",
      members: ["Traveler 1", "Traveler 2"],
    },
  ],
  requirements: {
    min_activities: 2,
    interest_coverage: true,
    max_regroup_gap_min: 15,
  },
  weather: {
    "9": 0.1, "10": 0.1, "11": 0.1, "12": 0.1,
    "13": 0.2, "14": 0.1, "15": 0.1, "16": 0.1,
    "17": 0.1, "18": 0.1, "19": 0.1, "20": 0.1,
  },
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [setup, setSetup] = useState<Setup>(DEFAULT_SETUP);
  const [plan, setPlan] = useState<PlanOutput | null>(null);
  const [initialPlanSnapshot, setInitialPlanSnapshot] = useState<PlanOutput | null>(null);
  const [activeDay, setActiveDay] = useState<number>(1);
  const [currentEvent, setCurrentEvent] = useState<AgentStepEvent | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [dataMode, setDataMode] = useState<string>("Live API Connected");
  const [venuesMap, setVenuesMap] = useState<Record<string, any>>({});
  const [streamError, setStreamError] = useState<string | null>(null);

  // Replan states
  const [isReplanning, setIsReplanning] = useState(false);
  const [replanDiff, setReplanDiff] = useState<ReplanDiff | null>(null);
  const [replanModifiedVenueIds, setReplanModifiedVenueIds] = useState<string[]>([]);

  // UI Drawer & Modal states
  const [selectedVenueId, setSelectedVenueId] = useState<string | null>("din_tai_fung_101");
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isAddStopOpen, setIsAddStopOpen] = useState(false);

  // Health check on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error("Health check failed");
        return res.json();
      })
      .then((data) => {
        setBackendHealthy(true);
        if (data.data_mode) {
          setDataMode(data.data_mode);
        }
      })
      .catch(() => {
        setBackendHealthy(false);
      });
  }, []);

  // Fetch venue metadata whenever city changes
  useEffect(() => {
    const city = setup.city || "taipei";
    fetch(`${API_BASE}/api/venues?city=${city}`)
      .then((res) => {
        if (!res.ok) throw new Error("Venues fetch failed");
        return res.json();
      })
      .then((data) => {
        setVenuesMap(data);
      })
      .catch((err) => {
        console.warn("Could not fetch live venues:", err);
      });
  }, [setup.city]);

  // Run Plan Stream using SSE
  const runPlanStream = async (targetSetup: Setup) => {
    setIsStreaming(true);
    setStreamError(null);
    setReplanDiff(null);
    setReplanModifiedVenueIds([]);
    setCurrentEvent({
      event: "start",
      node: "orchestrator",
      message: `Initializing multi-agent workflow for ${targetSetup.city.toUpperCase()} (${targetSetup.travelers.length} travelers)...`,
    });

    let receivedFinished = false;

    try {
      const response = await fetch(`${API_BASE}/api/plan/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_request: `Plan ${targetSetup.travelers.length}-person group trip in ${targetSetup.city}`,
          setup: targetSetup,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Stream response error");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed.startsWith("data: ")) continue;
          try {
            const data: AgentStepEvent = JSON.parse(trimmed.slice(6));
            setCurrentEvent(data);

            if (data.event === "error" || (data as any).step === "error") {
              setStreamError(data.message || "An unexpected error occurred during multi-agent planning.");
            }

            if (data.event === "finished" && data.plan) {
              receivedFinished = true;
              setStreamError(null);
              setPlan(data.plan);
              setInitialPlanSnapshot(data.plan);
              setActiveDay(1);
              if ((data as any).venues) {
                setVenuesMap((data as any).venues);
              }
              if (data.plan.itinerary && data.plan.itinerary.length > 0) {
                setSelectedVenueId(data.plan.itinerary[0].venue_id);
              }
            }
          } catch (e) {
            console.error("JSON parse error:", e);
          }
        }
      }

      if (!receivedFinished) {
        setStreamError("Stream closed before itinerary synthesis completed.");
      }
    } catch (err: any) {
      console.warn("Stream error encountered:", err);
      setStreamError(err?.message || "Failed to connect to backend planning engine.");
    } finally {
      if (receivedFinished) {
        setIsStreaming(false);
      }
    }
  };

  // 1. One-click load Taipei preset
  const handleLoadPreset = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/demo/taipei-preset`);
      if (res.ok) {
        const data = await res.json();
        setSetup(data.setup);
        await runPlanStream(data.setup);
      } else {
        await runPlanStream(DEFAULT_SETUP);
      }
    } catch {
      await runPlanStream(DEFAULT_SETUP);
    }
  };

  // 2. Trigger rain spike replan
  const handleTriggerRainSpike = async () => {
    if (!plan) return;
    setIsReplanning(true);

    try {
      const res = await fetch(`${API_BASE}/api/plan/replan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_plan: plan,
          setup: setup,
          event: {
            type: "rain_spike",
            time: "14:00",
            rain_prob: 85.0,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPlan(data.updated_plan);
        setReplanDiff(data.diff);

        // Highlight modified venue
        const modifiedIds = data.diff.modified_groups.map((m: any) => m.new_item.venue_id);
        setReplanModifiedVenueIds(modifiedIds);
        if (modifiedIds.length > 0) {
          setSelectedVenueId(modifiedIds[0]);
        }
      }
    } catch (err) {
      console.error("Replan error:", err);
    } finally {
      setIsReplanning(false);
    }
  };

  // 3. Reset Replan back to initial sunny plan
  const handleResetReplan = () => {
    if (initialPlanSnapshot) {
      setPlan(initialPlanSnapshot);
      setReplanDiff(null);
      setReplanModifiedVenueIds([]);
    }
  };

  // 4. Return from Workspace to Onboarding State
  const handleResetToOnboarding = () => {
    setPlan(null);
    setInitialPlanSnapshot(null);
    setReplanDiff(null);
    setReplanModifiedVenueIds([]);
    setCurrentEvent(null);
    setStreamError(null);
    setIsStreaming(false);
  };

  // 5. Select venue and open detail drawer
  const handleSelectVenue = (vid: string) => {
    setSelectedVenueId(vid);
    setIsDetailOpen(true);
  };

  // 6. Custom intake submit
  const handleIntakeSubmit = (newSetup: Setup) => {
    setSetup(newSetup);
    runPlanStream(newSetup);
  };

  // 7. Interactive Itinerary Edit
  const handleUpdateItem = (
    venueId: string,
    updates: { name: string; start: string; end: string; note?: string }
  ) => {
    if (venuesMap[venueId]) {
      setVenuesMap((prev) => ({
        ...prev,
        [venueId]: {
          ...prev[venueId],
          name: updates.name,
        },
      }));
    }

    setPlan((prev) => {
      if (!prev) return prev;
      const updatedItinerary = prev.itinerary.map((it) => {
        if (it.venue_id === venueId) {
          return {
            ...it,
            start: updates.start,
            end: updates.end,
            note: updates.note,
          };
        }
        return it;
      });
      return {
        ...prev,
        itinerary: updatedItinerary,
      };
    });
  };

  // 8. Add Custom Stop
  const handleAddCustomStop = (data: {
    name: string;
    start: string;
    end: string;
    cost: number;
    indoor: boolean;
    members: string[];
    note?: string;
  }) => {
    const customId = `custom_${Date.now()}`;
    const newVenue = {
      id: customId,
      name: data.name,
      cost: data.cost,
      indoor: data.indoor,
      walk: 1,
      open: "08:00",
      close: "22:00",
      tags: ["custom"],
      description: data.note || "Custom stop added by user.",
    };

    setVenuesMap((prev) => ({
      ...prev,
      [customId]: newVenue,
    }));

    setPlan((prev) => {
      if (!prev) return prev;
      const newItem: ItineraryItem = {
        venue_id: customId,
        start: data.start,
        end: data.end,
        members: data.members,
        note: data.note,
        is_custom: true,
      };
      const updated = [...prev.itinerary, newItem].sort((a, b) =>
        a.start.localeCompare(b.start)
      );
      return {
        ...prev,
        itinerary: updated,
      };
    });

    setReplanModifiedVenueIds((prev) => [...prev, customId]);
    setSelectedVenueId(customId);
  };

  const selectedItem =
    plan?.itinerary?.find((it) => it.venue_id === selectedVenueId) || null;
  const isSelectedAnchor =
    setup.anchors.some((a) => a.venue_id === selectedVenueId) ||
    selectedVenueId === "din_tai_fung_101";

  // =========================================================================
  // STATE A: Onboarding Empty State (Linear style clean canvas)
  // =========================================================================
  if (!plan && !isStreaming) {
    return (
      <>
        <OnboardingState
          onLoadPreset={handleLoadPreset}
          onOpenIntake={() => setIsIntakeOpen(true)}
          backendHealthy={backendHealthy}
          dataMode={dataMode}
        />
        <IntakeModal
          isOpen={isIntakeOpen}
          onClose={() => setIsIntakeOpen(false)}
          setup={setup}
          onSubmit={handleIntakeSubmit}
          isStreaming={isStreaming}
        />
      </>
    );
  }

  // =========================================================================
  // STATE B: Clean Stepper (Minimalist 4-step progress while streaming)
  // =========================================================================
  if (isStreaming) {
    return (
      <CleanStepper
        currentEvent={currentEvent}
        errorMessage={streamError}
        onRetry={() => runPlanStream(setup)}
        onReset={handleResetToOnboarding}
      />
    );
  }

  // =========================================================================
  // STATE C: Dual-Pane Workspace (Apple Maps + Linear Minimalist Layout)
  // =========================================================================
  return (
    <div className="min-h-screen flex flex-col bg-[#F9FAFB] text-gray-900">
      {/* Minimal Top Navbar (56px) */}
      <MinimalNavbar
        city={plan?.city || setup.city.toUpperCase()}
        backendHealthy={backendHealthy}
        dataMode={dataMode}
        onReset={handleResetToOnboarding}
        onOpenIntake={() => setIsIntakeOpen(true)}
        onOpenAudit={() => setIsAuditOpen(true)}
      />

      {/* Main Full-Width Stacked Workspace (Timeline on top, Interactive Map below) */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-8">
        {/* Top: Synchronized Multi-Track Swimlane (100% Full Width) */}
        <section className="w-full space-y-3.5">
          {/* Replan Notification Alert */}
          <ReplanDiffBanner diff={replanDiff} onDismiss={() => setReplanDiff(null)} />

          {/* Timeline */}
          <SwimlaneTimeline
            plan={plan}
            travelers={setup.travelers}
            selectedVenueId={selectedVenueId}
            onSelectVenue={handleSelectVenue}
            replanModifiedVenueIds={replanModifiedVenueIds}
            venuesMap={venuesMap}
            onOpenAddStop={() => setIsAddStopOpen(true)}
            activeDay={activeDay}
            onDayChange={setActiveDay}
          />
        </section>

        {/* Bottom: Apple Maps Style Interactive Map (100% Full Width) */}
        <section className="w-full relative flex flex-col space-y-2">
          <div className="flex items-center justify-between pb-1 border-b border-gray-200">
            <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
              Interactive Route Map & Directional Flow
            </span>
            <span className="text-[11px] text-gray-500 font-mono">
              Day {activeDay} · Synchronized Waypoints & Numbered Pins
            </span>
          </div>

          <div className="relative w-full h-[540px] rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
            {/* Minimalist Floating Scenario Simulator (Top-Right of Map) */}
            <DisruptionSimulator
              onTriggerRainSpike={handleTriggerRainSpike}
              onResetReplan={handleResetReplan}
              isReplanActive={Boolean(replanDiff)}
              isLoading={isReplanning}
              disabled={!plan || isStreaming}
            />

            <InteractiveMap
              plan={plan}
              selectedVenueId={selectedVenueId}
              onSelectVenue={handleSelectVenue}
              venuesMap={venuesMap}
              activeDay={activeDay}
            />
          </div>
        </section>
      </main>

      {/* Modals & Detail Drawers */}
      <IntakeModal
        isOpen={isIntakeOpen}
        onClose={() => setIsIntakeOpen(false)}
        setup={setup}
        onSubmit={handleIntakeSubmit}
        isStreaming={isStreaming}
      />

      <AuditDrawer
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
      />

      <VenueDetailDrawer
        isOpen={isDetailOpen}
        venue={selectedVenueId ? getVenue(selectedVenueId, venuesMap) : null}
        item={selectedItem}
        isAnchor={isSelectedAnchor}
        onClose={() => setIsDetailOpen(false)}
        onUpdateItem={handleUpdateItem}
      />

      <AddCustomStopModal
        isOpen={isAddStopOpen}
        onClose={() => setIsAddStopOpen(false)}
        travelers={setup.travelers}
        onAddStop={handleAddCustomStop}
      />
    </div>
  );
}
