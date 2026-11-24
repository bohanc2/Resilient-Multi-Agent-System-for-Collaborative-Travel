export interface Traveler {
  name: string;
  interests: string[];
  max_walk: number;
  budget: number;
}

export interface Anchor {
  venue_id: string;
  start: string;
  end: string;
  members: string[] | "all";
}

export interface Requirements {
  min_activities: number;
  interest_coverage: boolean;
  max_regroup_gap_min: number;
}

export interface Setup {
  city: string;
  weekday: string;
  day_start: string;
  day_end: string;
  start_location: string;
  travelers: Traveler[];
  anchors: Anchor[];
  requirements: Requirements;
  weather?: Record<string, number>;
}

export interface ItineraryItem {
  venue_id: string;
  start: string;
  end: string;
  members: string[];
}

export interface PlanOutput {
  feasible: boolean;
  reason: string;
  itinerary: ItineraryItem[];
  status?: string;
}

export interface VenueInfo {
  id: string;
  name: string;
  lat: number;
  lon: number;
  indoor: boolean;
  tags: string[];
  cost: number;
  walk: number;
  open: string;
  close: string;
  min_minutes: number;
  description: string;
}

export interface AgentStepEvent {
  event: "start" | "node_start" | "node_complete" | "finished";
  node?: "orchestrator" | "base_planner" | "group_sync" | "checker" | "supervisor" | "contingency";
  message: string;
  plan?: PlanOutput;
}

export interface ModifiedGroup {
  members: string[];
  status: "REPLACED";
  reason: string;
  original_item: {
    venue_id: string;
    name: string;
    start: string;
    end: string;
    indoor: boolean;
  };
  new_item: {
    venue_id: string;
    name: string;
    start: string;
    end: string;
    indoor: boolean;
  };
}

export interface UnaffectedGroup {
  members: string[];
  status: "UNCHANGED";
  venue_id: string;
  name: string;
  start: string;
  end: string;
  indoor: boolean;
}

export interface ReplanDiff {
  event_summary: string;
  modified_count: number;
  unaffected_count: number;
  modified_groups: ModifiedGroup[];
  unaffected_groups: UnaffectedGroup[];
}

export interface ReplanResponse {
  event: {
    type: string;
    time: string;
    rain_prob: number;
  };
  diff: ReplanDiff;
  updated_plan: PlanOutput;
}
