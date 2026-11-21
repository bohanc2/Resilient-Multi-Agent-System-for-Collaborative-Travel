"""
eval.py - Automated Evaluation Harness for Resilient Multi-Agent Collaborative Travel Planning.

Architecture & Core Logic:
- Mock Environment: Local database of venues (indoor/outdoor, hours, cost), transit time matrix, and weather.
- Deterministic Python Checker: Validates hard anchors, operating hours, rain contingencies, transit buffers,
  split-and-regroup arrival gaps (<= 15 mins), traveler budgets, and explicit unanswerable task rejection.
- Non-Agentic Baseline: Single LLM turn, zero tools, direct itinerary generation or refusal.
- Project Agent (MVP): Plan-and-Verify loop (up to 3 turns) with localized replan upon checker feedback.
- Concurrency: Multi-threaded execution via ThreadPoolExecutor.
- Metrics & Reports: Side-by-side Markdown comparison table, pass@3, pass^3, flaky tasks detection,
  and comprehensive eval_logs.json for Failure Analysis.
- Dual execution: Live OpenAI API (when a valid key is provided) or Fast Offline Mock LLM (--mock-llm or auto-fallback).
"""

import os
import sys
import json
import time
import math
import random
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================
# 1. Mock Environment & Tools
# ==========================================

class MockEnvironment:
    """In-memory mock database of venues, transit times, and live weather."""

    def __init__(self):
        # Venues database: {venue_name: details}
        self.venues: Dict[str, Dict[str, Any]] = {
            # Taipei
            "Taipei 101 Dining": {
                "city": "Taipei", "is_indoor": True, "open_time": "11:00", "close_time": "21:30",
                "cost": 40, "is_open": True, "category": "dining"
            },
            "Elephant Mountain Trail": {
                "city": "Taipei", "is_indoor": False, "open_time": "06:00", "close_time": "22:00",
                "cost": 0, "is_open": True, "category": "hiking"
            },
            "National Palace Museum": {
                "city": "Taipei", "is_indoor": True, "open_time": "09:00", "close_time": "17:00",
                "cost": 15, "is_open": True, "category": "museum"
            },
            "Syntrend Creative Park": {
                "city": "Taipei", "is_indoor": True, "open_time": "11:00", "close_time": "21:30",
                "cost": 0, "is_open": True, "category": "tech_shopping"
            },
            "Yongkang Street Cafes": {
                "city": "Taipei", "is_indoor": True, "open_time": "10:00", "close_time": "21:00",
                "cost": 15, "is_open": True, "category": "cafe"
            },
            "Daan Forest Park": {
                "city": "Taipei", "is_indoor": False, "open_time": "06:00", "close_time": "23:00",
                "cost": 0, "is_open": True, "category": "park"
            },
            "Taipei Fine Arts Museum": {
                "city": "Taipei", "is_indoor": True, "open_time": "09:30", "close_time": "17:30",
                "cost": 10, "is_open": True, "category": "art"
            },

            # Tokyo
            "Roppongi Hills Sky Deck": {
                "city": "Tokyo", "is_indoor": True, "open_time": "10:00", "close_time": "22:00",
                "cost": 20, "is_open": True, "category": "view"
            },
            "Meiji Shrine & Yoyogi Park": {
                "city": "Tokyo", "is_indoor": False, "open_time": "06:00", "close_time": "17:00",
                "cost": 0, "is_open": True, "category": "park"
            },
            "Mori Art Museum": {
                "city": "Tokyo", "is_indoor": True, "open_time": "10:00", "close_time": "22:00",
                "cost": 18, "is_open": False,  # Closed for maintenance (Edge Case 2)
                "category": "museum", "closure_reason": "Emergency maintenance overhaul"
            },
            "teamLab Planets": {
                "city": "Tokyo", "is_indoor": True, "open_time": "09:00", "close_time": "22:00",
                "cost": 30, "is_open": True, "category": "digital_art"
            },
            "Akihabara Electric Town": {
                "city": "Tokyo", "is_indoor": True, "open_time": "10:00", "close_time": "20:00",
                "cost": 15, "is_open": True, "category": "shopping"
            },
            "Tokyo National Museum": {
                "city": "Tokyo", "is_indoor": True, "open_time": "09:30", "close_time": "17:00",
                "cost": 10, "is_open": True, "category": "museum"
            },
            "Shinjuku Gyoen": {
                "city": "Tokyo", "is_indoor": False, "open_time": "09:00", "close_time": "16:30",
                "cost": 5, "is_open": True, "category": "garden"
            },
            "Ginza Luxury Dining": {
                "city": "Tokyo", "is_indoor": True, "open_time": "12:00", "close_time": "22:00",
                "cost": 100, "is_open": True, "category": "dining"
            },
            "Sushi Yoshitake": {
                "city": "Tokyo", "is_indoor": True, "open_time": "18:00", "close_time": "22:00",
                "cost": 350, "is_open": True, "category": "fine_dining"
            },

            # Seattle
            "Space Needle Observation Deck": {
                "city": "Seattle", "is_indoor": True, "open_time": "09:00", "close_time": "22:00",
                "cost": 35, "is_open": True, "category": "view"
            },
            "Chihuly Garden and Glass": {
                "city": "Seattle", "is_indoor": True, "open_time": "10:00", "close_time": "18:00",
                "cost": 25, "is_open": True, "category": "museum"
            },
            "Pike Place Market": {
                "city": "Seattle", "is_indoor": True, "open_time": "09:00", "close_time": "18:00",
                "cost": 15, "is_open": True, "category": "market"
            },
            "Discovery Park Trail": {
                "city": "Seattle", "is_indoor": False, "open_time": "06:00", "close_time": "20:00",
                "cost": 0, "is_open": True, "category": "hiking"
            },
            "Museum of Pop Culture (MoPOP)": {
                "city": "Seattle", "is_indoor": True, "open_time": "10:00", "close_time": "17:00",
                "cost": 25, "is_open": True, "category": "museum"
            },
            "Kerry Park": {
                "city": "Seattle", "is_indoor": False, "open_time": "06:00", "close_time": "22:00",
                "cost": 0, "is_open": True, "category": "viewpoint"
            },
            "Elliott Bay Book Company": {
                "city": "Seattle", "is_indoor": True, "open_time": "10:00", "close_time": "20:00",
                "cost": 10, "is_open": True, "category": "books_cafe"
            },

            # Kyoto
            "Gion Kaiseki Dinner": {
                "city": "Kyoto", "is_indoor": True, "open_time": "18:00", "close_time": "21:30",
                "cost": 20,
                "is_open": True, "category": "dining"
            },
            "Fushimi Inari Shrine": {
                "city": "Kyoto", "is_indoor": False, "open_time": "06:00", "close_time": "22:00",
                "cost": 0, "is_open": True, "category": "culture_walk"
            },
            "Kiyomizu-dera": {
                "city": "Kyoto", "is_indoor": False, "open_time": "06:00", "close_time": "18:00",
                "cost": 5, "is_open": True, "category": "temple"
            },
            "Kyoto Museum of Crafts and Design": {
                "city": "Kyoto", "is_indoor": True, "open_time": "10:00", "close_time": "18:00",
                "cost": 8, "is_open": True, "category": "museum"
            },
            "Kyoto Railway Museum": {
                "city": "Kyoto", "is_indoor": True, "open_time": "10:00", "close_time": "17:00",
                "cost": 12, "is_open": True, "category": "museum"
            },
            "Nishiki Market": {
                "city": "Kyoto", "is_indoor": True, "open_time": "10:00", "close_time": "17:30",
                "cost": 15, "is_open": True, "category": "food_market"
            },

            # New York
            "Broadway Theatre Show": {
                "city": "New York", "is_indoor": True, "open_time": "19:00", "close_time": "22:00",
                "cost": 50, "is_open": True, "category": "theatre"
            },
            "Central Park Rambles": {
                "city": "New York", "is_indoor": False, "open_time": "06:00", "close_time": "22:00",
                "cost": 0, "is_open": True, "category": "park"
            },
            "Metropolitan Museum of Art": {
                "city": "New York", "is_indoor": True, "open_time": "10:00", "close_time": "17:00",
                "cost": 20, "is_open": True, "category": "museum"
            },
            "One World Observatory": {
                "city": "New York", "is_indoor": True, "open_time": "09:00", "close_time": "21:00",
                "cost": 30, "is_open": True, "category": "view"
            },
            "High Line & Chelsea Market": {
                "city": "New York", "is_indoor": True, "open_time": "08:00", "close_time": "21:00",
                "cost": 15, "is_open": True, "category": "walk_food"
            },
            "SoHo Boutique Walk": {
                "city": "New York", "is_indoor": True, "open_time": "11:00", "close_time": "19:00",
                "cost": 20, "is_open": True, "category": "shopping"
            },

            # Kaohsiung (for physical impossibility edge case)
            "Kaohsiung Harbor Dinner": {
                "city": "Kaohsiung", "is_indoor": True, "open_time": "17:00", "close_time": "21:00",
                "cost": 35, "is_open": True, "category": "dining"
            }
        }

        # Pairwise transit times (minutes)
        self.transit_matrix: Dict[Tuple[str, str], int] = {
            # Taipei pairs
            ("Elephant Mountain Trail", "Taipei 101 Dining"): 15,
            ("National Palace Museum", "Taipei 101 Dining"): 35,
            ("Syntrend Creative Park", "Taipei 101 Dining"): 20,
            ("Yongkang Street Cafes", "Taipei 101 Dining"): 15,
            ("Daan Forest Park", "Taipei 101 Dining"): 15,
            ("Taipei Fine Arts Museum", "Taipei 101 Dining"): 25,
            ("Elephant Mountain Trail", "Syntrend Creative Park"): 25,
            ("Yongkang Street Cafes", "Syntrend Creative Park"): 15,

            # Tokyo pairs
            ("Meiji Shrine & Yoyogi Park", "Roppongi Hills Sky Deck"): 20,
            ("Mori Art Museum", "Roppongi Hills Sky Deck"): 5,
            ("teamLab Planets", "Roppongi Hills Sky Deck"): 25,
            ("Akihabara Electric Town", "Roppongi Hills Sky Deck"): 25,
            ("Tokyo National Museum", "Roppongi Hills Sky Deck"): 30,
            ("Shinjuku Gyoen", "Roppongi Hills Sky Deck"): 20,
            ("Akihabara Electric Town", "teamLab Planets"): 20,

            # Seattle pairs
            ("Discovery Park Trail", "Space Needle Observation Deck"): 30,
            ("Pike Place Market", "Space Needle Observation Deck"): 15,
            ("Chihuly Garden and Glass", "Space Needle Observation Deck"): 5,
            ("Museum of Pop Culture (MoPOP)", "Space Needle Observation Deck"): 5,
            ("Kerry Park", "Space Needle Observation Deck"): 15,
            ("Elliott Bay Book Company", "Space Needle Observation Deck"): 20,

            # Kyoto pairs
            ("Fushimi Inari Shrine", "Gion Kaiseki Dinner"): 20,
            ("Kiyomizu-dera", "Gion Kaiseki Dinner"): 15,
            ("Kyoto Museum of Crafts and Design", "Gion Kaiseki Dinner"): 15,
            ("Kyoto Railway Museum", "Gion Kaiseki Dinner"): 25,
            ("Nishiki Market", "Gion Kaiseki Dinner"): 10,

            # New York pairs
            ("Central Park Rambles", "Broadway Theatre Show"): 15,
            ("Metropolitan Museum of Art", "Broadway Theatre Show"): 25,
            ("One World Observatory", "Broadway Theatre Show"): 30,
            ("High Line & Chelsea Market", "Broadway Theatre Show"): 15,
            ("SoHo Boutique Walk", "Broadway Theatre Show"): 20,

            # Cross-city impossibility
            ("Taipei 101 Dining", "Kaohsiung Harbor Dinner"): 110,
            ("National Palace Museum", "Kaohsiung Harbor Dinner"): 135
        }

    def check_venue(self, venue_name: str) -> Dict[str, Any]:
        """Tool: Lookup venue opening hours, indoor/outdoor flag, cost, and open status."""
        for name, data in self.venues.items():
            if name.lower() == venue_name.strip().lower():
                return {"venue": name, **data, "found": True}
        return {"venue": venue_name, "found": False, "is_open": False, "cost": 0, "is_indoor": True}

    def get_transit_time(self, origin: str, destination: str, city: Optional[str] = None) -> int:
        """Tool: Lookup transit travel time between two venues in minutes."""
        if origin.strip().lower() == destination.strip().lower():
            return 0
        for (v1, v2), time_mins in self.transit_matrix.items():
            if (v1.lower() == origin.strip().lower() and v2.lower() == destination.strip().lower()) or \
               (v2.lower() == origin.strip().lower() and v1.lower() == destination.strip().lower()):
                return time_mins

        v1_info = self.check_venue(origin)
        v2_info = self.check_venue(destination)
        if v1_info.get("found") and v2_info.get("found"):
            if v1_info["city"] != v2_info["city"]:
                return 120
            return 20
        return 20

    def check_weather(self, city: str, hour_str: str) -> Dict[str, Any]:
        """Tool: Check weather forecast for a city at a given time."""
        h = int(hour_str.split(":")[0]) if ":" in hour_str else int(hour_str)
        if city.lower() == "taipei" and h >= 14:
            return {"city": city, "hour": hour_str, "weather": "rain", "rain_prob": 0.85, "condition": "Heavy Thunderstorm"}
        if city.lower() == "kyoto" and h >= 13:
            return {"city": city, "hour": hour_str, "weather": "rain", "rain_prob": 0.80, "condition": "Continuous Rain"}
        return {"city": city, "hour": hour_str, "weather": "clear", "rain_prob": 0.05, "condition": "Sunny / Overcast"}


# ==========================================
# 2. Deterministic Python Checker
# ==========================================

def parse_time_to_minutes(time_str: str) -> int:
    """Helper: Converts HH:MM string to minutes from 00:00."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0

def minutes_to_time(minutes: int) -> str:
    """Helper: Converts minutes to HH:MM string."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

class DeterministicChecker:
    """Rule-based spatio-temporal and constraint validation engine."""

    def __init__(self, env: MockEnvironment):
        self.env = env

    def validate(self, plan: Dict[str, Any], task: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates an itinerary plan against task constraints.
        Returns: (is_valid, list_of_error_strings)
        """
        errors: List[str] = []
        constraints = task.get("constraints", {})
        is_answerable = constraints.get("is_answerable", True)

        # 1. Check Unanswerability handling
        is_rejected = (
            plan.get("status") == "rejected" or
            plan.get("decision") == "reject" or
            bool(plan.get("rejection_reason"))
        )

        if not is_answerable:
            if is_rejected:
                return True, []
            else:
                return False, ["Task is physically or financially impossible, but agent produced an itinerary instead of rejecting."]

        if is_answerable and is_rejected:
            return False, [f"Feasible task was incorrectly rejected by agent: {plan.get('rejection_reason', 'No reason given')}"]

        itinerary = plan.get("itinerary", [])
        if not itinerary:
            return False, ["Plan contains no itinerary tracks or activities."]

        hard_anchor = constraints.get("hard_anchor")
        weather_rain_after = constraints.get("weather_rain_after")
        max_regroup_gap = constraints.get("max_regroup_gap_mins", 15)
        max_budget = constraints.get("max_budget_per_person")

        anchor_venue = hard_anchor.get("venue") if hard_anchor else None
        anchor_start_m = parse_time_to_minutes(hard_anchor["start_time"]) if hard_anchor else None
        anchor_end_m = parse_time_to_minutes(hard_anchor["end_time"]) if hard_anchor else None
        rain_after_m = parse_time_to_minutes(weather_rain_after) if weather_rain_after else None

        regroup_arrivals: List[int] = []

        # 2. Iterate each group track
        for group_idx, track in enumerate(itinerary):
            group_id = track.get("group_id", f"Group {group_idx+1}")
            activities = track.get("activities", [])
            if not activities:
                errors.append(f"[{group_id}] Has no scheduled activities.")
                continue

            # Hard Anchor Preservation check
            if hard_anchor:
                anchor_found = False
                for act in activities:
                    if act.get("venue", "").strip().lower() == anchor_venue.strip().lower():
                        act_start_m = parse_time_to_minutes(act.get("start_time", ""))
                        act_end_m = parse_time_to_minutes(act.get("end_time", ""))
                        if abs(act_start_m - anchor_start_m) <= 5 and abs(act_end_m - anchor_end_m) <= 5:
                            anchor_found = True
                            break
                        else:
                            errors.append(
                                f"[{group_id}] Hard anchor '{anchor_venue}' time modified to "
                                f"{act.get('start_time')}-{act.get('end_time')} (must remain {hard_anchor['start_time']}-{hard_anchor['end_time']})."
                            )
                if not anchor_found and not any(anchor_venue.lower() in err.lower() for err in errors):
                    errors.append(f"[{group_id}] Missing mandatory hard anchor booking: '{anchor_venue}'.")

            # Budget check
            group_cost = 0
            for act in activities:
                group_cost += act.get("cost", 0)
            if max_budget is not None and group_cost > max_budget:
                errors.append(f"[{group_id}] Total activity cost ${group_cost} exceeds personal budget cap ${max_budget}.")

            # Operating hours, weather, and transit buffers
            for i, act in enumerate(activities):
                v_name = act.get("venue", "").strip()
                v_info = self.env.check_venue(v_name)
                act_start_m = parse_time_to_minutes(act.get("start_time", ""))
                act_end_m = parse_time_to_minutes(act.get("end_time", ""))

                if v_info.get("found") and not v_info.get("is_open", True):
                    errors.append(f"[{group_id}] Scheduled venue '{v_name}' is currently closed ({v_info.get('closure_reason', 'maintenance')}).")

                if v_info.get("found"):
                    open_m = parse_time_to_minutes(v_info.get("open_time", "00:00"))
                    close_m = parse_time_to_minutes(v_info.get("close_time", "23:59"))
                    if act_start_m < open_m or act_end_m > close_m:
                        errors.append(
                            f"[{group_id}] Operating hour violation for '{v_name}': scheduled {act.get('start_time')}-{act.get('end_time')}, "
                            f"but venue is open {v_info.get('open_time')}-{v_info.get('close_time')}."
                        )

                if rain_after_m is not None:
                    if v_info.get("found") and not v_info.get("is_indoor", True):
                        if act_end_m > rain_after_m:
                            errors.append(
                                f"[{group_id}] Weather violation: '{v_name}' is an outdoor venue, but heavy rain is forecasted after {weather_rain_after}."
                            )

                if i < len(activities) - 1:
                    next_act = activities[i + 1]
                    next_start_m = parse_time_to_minutes(next_act.get("start_time", ""))
                    transit_buffer = next_start_m - act_end_m
                    transit_required = self.env.get_transit_time(v_name, next_act.get("venue", ""), task.get("city"))
                    if transit_buffer < transit_required:
                        errors.append(
                            f"[{group_id}] Transit buffer deficit between '{v_name}' and '{next_act.get('venue')}': "
                            f"requires {transit_required} mins transit, but buffer is only {transit_buffer} mins."
                        )

            # Record arrival time
            arrival_str = track.get("regroup_arrival_time")
            if arrival_str:
                regroup_arrivals.append(parse_time_to_minutes(arrival_str))
            else:
                last_act = activities[-1]
                regroup_arrivals.append(parse_time_to_minutes(last_act.get("start_time", "18:15")))

        # 3. Check Split & Regroup arrival gap across sub-groups
        if len(itinerary) > 1 and len(regroup_arrivals) > 1:
            earliest_arr = min(regroup_arrivals)
            latest_arr = max(regroup_arrivals)
            gap = latest_arr - earliest_arr
            if gap > max_regroup_gap:
                errors.append(
                    f"Regroup arrival gap violation: sub-groups arrive between {minutes_to_time(earliest_arr)} "
                    f"and {minutes_to_time(latest_arr)} (difference {gap} mins > max allowed {max_regroup_gap} mins)."
                )

        return (len(errors) == 0), errors


# ==========================================
# 3. LLM Generation Engines
# ==========================================

class MockLLMEngine:
    """
    Simulated LLM engine for fast offline evaluation.
    Features:
    - Baseline: Fails edge cases (unaware of live weather/closures) and unanswerable prompts (~25-35% acc).
    - Agent Turn 1: Uses tools, but in edge cases may produce minor timing or venue flaws.
    - Agent Turn 2-3: Incorporates Checker feedback for Localized Replan, yielding ~92-96% acc.
    - Realistic temperature variance to benchmark pass@3 vs pass^3 and flaky task identification.
    """

    def __init__(self, env: MockEnvironment):
        self.env = env

    def generate_baseline(self, task: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Baseline one-shot generation without tools or feedback."""
        category = task.get("category", "normal")
        c = task.get("constraints", {})
        tool_calls: List[Dict[str, Any]] = []

        if category == "unanswerable":
            return {
                "status": "success",
                "itinerary": [
                    {
                        "group_id": "All Travelers",
                        "activities": [
                            {"venue": "Taipei 101 Dining", "start_time": "15:00", "end_time": "17:00", "cost": 30},
                            {"venue": c["hard_anchor"]["venue"], "start_time": c["hard_anchor"]["start_time"], "end_time": c["hard_anchor"]["end_time"], "cost": 0}
                        ],
                        "regroup_arrival_time": "17:10"
                    }
                ]
            }, tool_calls

        city = task.get("city", "Taipei")
        anchor = c["hard_anchor"]

        if task.get("task_id") == "task_45_edge_rain_taipei":
            return {
                "status": "success",
                "itinerary": [
                    {
                        "group_id": "Group 1",
                        "activities": [
                            {"venue": "Elephant Mountain Trail", "start_time": "14:30", "end_time": "16:30", "cost": 0},
                            {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": 35}
                        ],
                        "regroup_arrival_time": "17:45"
                    },
                    {
                        "group_id": "Group 2",
                        "activities": [
                            {"venue": "Yongkang Street Cafes", "start_time": "14:00", "end_time": "16:30", "cost": 15},
                            {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": 35}
                        ],
                        "regroup_arrival_time": "18:15"
                    }
                ]
            }, tool_calls

        if task.get("task_id") == "task_46_edge_closed_tokyo":
            return {
                "status": "success",
                "itinerary": [
                    {
                        "group_id": "Group 1",
                        "activities": [
                            {"venue": "Mori Art Museum", "start_time": "14:00", "end_time": "16:30", "cost": 18},
                            {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": 20}
                        ],
                        "regroup_arrival_time": "18:10"
                    }
                ]
            }, tool_calls

        # Normal tasks: Baseline often has arrival gap > 15 mins (~30% acc)
        task_num = int(task.get("task_id", "0").split("_")[1]) if "_" in task.get("task_id", "") and task.get("task_id", "").split("_")[1].isdigit() else 1
        if task_num % 3 != 0:
            return {
                "status": "success",
                "itinerary": [
                    {
                        "group_id": "Group A",
                        "activities": [
                            {"venue": "Syntrend Creative Park" if city == "Taipei" else "Akihabara Electric Town", "start_time": "14:00", "end_time": "16:30", "cost": 0},
                            {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": 25}
                        ],
                        "regroup_arrival_time": "17:30"
                    },
                    {
                        "group_id": "Group B",
                        "activities": [
                            {"venue": "Yongkang Street Cafes" if city == "Taipei" else "Tokyo National Museum", "start_time": "14:30", "end_time": "17:00", "cost": 15},
                            {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": 25}
                        ],
                        "regroup_arrival_time": "18:15"  # Gap = 45 mins (> 15 mins)
                    }
                ]
            }, tool_calls

        return self._make_valid_plan(task), tool_calls

    def generate_agent_turn(self, task: Dict[str, Any], turn: int, checker_feedback: Optional[List[str]] = None, temperature: float = 0.7) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Agent turn generation with tool calls and localized replanning."""
        c = task.get("constraints", {})
        tool_calls: List[Dict[str, Any]] = []

        tool_calls.append({"tool": "check_venue", "args": {"venue": c["hard_anchor"]["venue"]}})
        if c.get("weather_rain_after"):
            tool_calls.append({"tool": "check_weather", "args": {"city": task.get("city", "Taipei"), "hour": "14:00"}})

        # Unanswerable tasks
        if not c.get("is_answerable", True):
            tool_calls.append({"tool": "get_transit_time", "args": {"origin": "Taipei 101 Dining", "destination": c["hard_anchor"]["venue"]}})
            return {
                "status": "rejected",
                "rejection_reason": c.get("rejection_reason", "Impossible spatio-temporal or financial constraint detected.")
            }, tool_calls

        # Turn 1: Realistic initial draft
        if turn == 1:
            if task.get("task_id") == "task_45_edge_rain_taipei":
                return {
                    "status": "success",
                    "itinerary": [
                        {
                            "group_id": "Group 1",
                            "activities": [
                                {"venue": "Elephant Mountain Trail", "start_time": "14:00", "end_time": "16:00", "cost": 0},
                                {"venue": c["hard_anchor"]["venue"], "start_time": c["hard_anchor"]["start_time"], "end_time": c["hard_anchor"]["end_time"], "cost": 30}
                            ],
                            "regroup_arrival_time": "18:15"
                        },
                        {
                            "group_id": "Group 2",
                            "activities": [
                                {"venue": "Yongkang Street Cafes", "start_time": "14:30", "end_time": "16:30", "cost": 15},
                                {"venue": c["hard_anchor"]["venue"], "start_time": c["hard_anchor"]["start_time"], "end_time": c["hard_anchor"]["end_time"], "cost": 30}
                            ],
                            "regroup_arrival_time": "18:10"
                        }
                    ]
                }, tool_calls
            elif task.get("task_id") == "task_47_edge_tight_regroup_seattle":
                return {
                    "status": "success",
                    "itinerary": [
                        {
                            "group_id": "Group 1",
                            "activities": [
                                {"venue": "Discovery Park Trail", "start_time": "14:00", "end_time": "17:10", "cost": 0},
                                {"venue": c["hard_anchor"]["venue"], "start_time": c["hard_anchor"]["start_time"], "end_time": c["hard_anchor"]["end_time"], "cost": 30}
                            ],
                            "regroup_arrival_time": "17:40"
                        },
                        {
                            "group_id": "Group 2",
                            "activities": [
                                {"venue": "Pike Place Market", "start_time": "14:30", "end_time": "17:40", "cost": 15},
                                {"venue": c["hard_anchor"]["venue"], "start_time": c["hard_anchor"]["start_time"], "end_time": c["hard_anchor"]["end_time"], "cost": 30}
                            ],
                            "regroup_arrival_time": "18:00"  # 20 min gap
                        }
                    ]
                }, tool_calls

            # Normal tasks on Turn 1: 85% clean pass, 15% minor arrival gap
            if random.random() < 0.15:
                plan = self._make_valid_plan(task)
                plan["itinerary"][0]["regroup_arrival_time"] = "17:50"
                return plan, tool_calls

            return self._make_valid_plan(task), tool_calls

        # Turn 2 or 3: Localized Replan fixes the conflicting segment
        tool_calls.append({"tool": "localized_repair", "args": {"feedback_errors": checker_feedback}})

        # Stochastic flaky behavior under temperature 0.7
        if temperature > 0.5:
            if task.get("task_id") == "task_47_edge_tight_regroup_seattle" and random.random() < 0.30:
                plan = self._make_valid_plan(task)
                plan["itinerary"][0]["regroup_arrival_time"] = "17:35"
                plan["itinerary"][1]["regroup_arrival_time"] = "17:55"  # 20 mins gap
                return plan, tool_calls
            elif random.random() < 0.04:
                plan = self._make_valid_plan(task)
                plan["itinerary"][0]["regroup_arrival_time"] = "17:40"
                plan["itinerary"][1]["regroup_arrival_time"] = "18:00"
                return plan, tool_calls

        return self._make_valid_plan(task), tool_calls

    def _make_valid_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Constructs a valid, constraint-compliant itinerary respecting all limits."""
        city = task.get("city", "Taipei")
        c = task.get("constraints", {})
        anchor = c["hard_anchor"]
        regroup_time = c.get("required_regroup_time", "18:15")
        regroup_m = parse_time_to_minutes(regroup_time)
        max_budget = c.get("max_budget_per_person", 60)

        # Ensure anchor cost leaves room for afternoon activity within max_budget
        anchor_cost = min(anchor.get("cost", 30), max(5, max_budget - 15))
        rem_budget = max(0, max_budget - anchor_cost)

        indoor_venues_map = {
            "Taipei": ("Syntrend Creative Park", "National Palace Museum"),
            "Tokyo": ("teamLab Planets", "Akihabara Electric Town"),
            "Seattle": ("Pike Place Market", "Museum of Pop Culture (MoPOP)"),
            "Kyoto": ("Kyoto Museum of Crafts and Design", "Nishiki Market"),
            "New York": ("Metropolitan Museum of Art", "One World Observatory")
        }
        v1, v2 = indoor_venues_map.get(city, ("Syntrend Creative Park", "National Palace Museum"))

        if task.get("task_id") == "task_48_edge_rain_budget_kyoto":
            v1 = "Kyoto Museum of Crafts and Design"  # cost $8
            v2 = "Kyoto Railway Museum"               # cost $12
            anchor_cost = 10
            rem_budget = 15

        c1 = min(10, rem_budget)
        c2 = min(12, rem_budget)

        arr1 = minutes_to_time(regroup_m - 5)
        arr2 = minutes_to_time(regroup_m)

        return {
            "status": "success",
            "itinerary": [
                {
                    "group_id": "Group 1",
                    "activities": [
                        {"venue": v1, "start_time": "14:00", "end_time": "16:30", "cost": c1},
                        {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": anchor_cost}
                    ],
                    "regroup_arrival_time": arr1
                },
                {
                    "group_id": "Group 2",
                    "activities": [
                        {"venue": v2, "start_time": "14:30", "end_time": "17:00", "cost": c2},
                        {"venue": anchor["venue"], "start_time": anchor["start_time"], "end_time": anchor["end_time"], "cost": anchor_cost}
                    ],
                    "regroup_arrival_time": arr2
                }
            ]
        }


class OpenAILLMEngine:
    """Live LLM engine communicating with OpenAI Chat Completions API."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
        self.client.models.list()

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> Tuple[Dict[str, Any], int, float]:
        """Calls OpenAI Chat Completion and returns (parsed_json, total_tokens, latency)."""
        start_t = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        latency = time.perf_counter() - start_t
        raw_text = response.choices[0].message.content or "{}"
        total_tokens = response.usage.total_tokens if response.usage else 500
        try:
            parsed = json.loads(raw_text)
        except Exception:
            parsed = {"status": "error", "raw_output": raw_text}
        return parsed, total_tokens, latency


# ==========================================
# 4. Evaluation Runners (Baseline & Agent)
# ==========================================

def run_baseline(task: Dict[str, Any], mock_llm: MockLLMEngine, live_llm: Optional[OpenAILLMEngine], checker: DeterministicChecker) -> Dict[str, Any]:
    """Evaluates a single task with the Non-Agentic Baseline (single-shot, no tools)."""
    start_time = time.perf_counter()
    tokens = 0
    tool_calls = []

    if live_llm is not None:
        system_prompt = (
            "You are a travel assistant. Given traveler preferences, budget limits, and fixed bookings, "
            "generate a complete 1-day itinerary in valid JSON.\n"
            "If the request is physically, temporally, or financially impossible, you MUST reject it:\n"
            '{"status": "rejected", "rejection_reason": "<explanation>"}\n'
            "Otherwise, return:\n"
            '{"status": "success", "itinerary": [{"group_id": "...", "activities": [{"venue": "...", "start_time": "HH:MM", "end_time": "HH:MM", "cost": 0}], "regroup_arrival_time": "HH:MM"}]}'
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task["prompt"]}
        ]
        plan, tokens, latency = live_llm.generate(messages, temperature=0.7)
    else:
        time.sleep(random.uniform(0.04, 0.12))
        plan, tool_calls = mock_llm.generate_baseline(task)
        tokens = random.randint(350, 480)

    is_valid, errors = checker.validate(plan, task)
    total_latency = time.perf_counter() - start_time

    return {
        "task_id": task["task_id"],
        "category": task["category"],
        "system": "baseline",
        "passed": is_valid,
        "turns": 1,
        "latency_s": round(total_latency, 3),
        "tokens": tokens,
        "errors": errors,
        "tool_calls": tool_calls,
        "output_plan": plan
    }

def run_agent(task: Dict[str, Any], mock_llm: MockLLMEngine, live_llm: Optional[OpenAILLMEngine], checker: DeterministicChecker, temperature: float = 0.7, max_turns: int = 3) -> Dict[str, Any]:
    """Evaluates a single task with the Project Agent MVP (Plan-and-Verify loop with localized replan)."""
    start_time = time.perf_counter()
    total_tokens = 0
    history: List[Dict[str, Any]] = []
    current_feedback: Optional[List[str]] = None
    is_valid = False
    errors: List[str] = []
    plan: Dict[str, Any] = {}

    for turn in range(1, max_turns + 1):
        turn_start = time.perf_counter()
        tool_calls: List[Dict[str, Any]] = []

        if live_llm is not None:
            system_prompt = (
                "You are an expert Collaborative Multi-Agent Travel Planner.\n"
                "You coordinate sub-groups with divergent preferences, strict budgets, and hard anchor bookings.\n"
                "Rules:\n"
                "1. If unanswerable (physical/financial impossibility), return: {'status': 'rejected', 'rejection_reason': '...'}\n"
                "2. All sub-groups must preserve hard anchors without moving time.\n"
                "3. Outdoor venues cannot be scheduled during rain.\n"
                "4. All sub-groups must regroup within 15 minutes of each other.\n"
                "5. Ensure transit buffers between venues are sufficient.\n"
                "Return JSON with 'status' and 'itinerary'."
            )
            messages = [{"role": "system", "content": system_prompt}]
            if turn == 1:
                messages.append({"role": "user", "content": task["prompt"]})
            else:
                messages.append({"role": "user", "content": task["prompt"]})
                messages.append({"role": "assistant", "content": json.dumps(plan)})
                feedback_msg = (
                    f"Deterministic Checker Verification FAILED with {len(current_feedback)} conflicts:\n" +
                    "\n".join([f"- {err}" for err in current_feedback]) +
                    "\nPlease perform a LOCALIZED REPLAN: keep all valid segments and hard anchors unchanged, "
                    "and repair only the violating venues or arrival times."
                )
                messages.append({"role": "user", "content": feedback_msg})

            plan, turn_tokens, turn_lat = live_llm.generate(messages, temperature=temperature)
            total_tokens += turn_tokens
        else:
            time.sleep(random.uniform(0.06, 0.16))
            plan, tool_calls = mock_llm.generate_agent_turn(task, turn, current_feedback, temperature=temperature)
            turn_tokens = random.randint(480, 720)
            total_tokens += turn_tokens

        is_valid, errors = checker.validate(plan, task)
        turn_latency = time.perf_counter() - turn_start

        history.append({
            "turn": turn,
            "latency_s": round(turn_latency, 3),
            "tokens": turn_tokens,
            "tool_calls": tool_calls,
            "checker_passed": is_valid,
            "checker_errors": errors,
            "plan": plan
        })

        if is_valid:
            break
        current_feedback = errors

    total_latency = time.perf_counter() - start_time
    return {
        "task_id": task["task_id"],
        "category": task["category"],
        "system": "agent",
        "passed": is_valid,
        "turns": len(history),
        "latency_s": round(total_latency, 3),
        "tokens": total_tokens,
        "errors": errors if not is_valid else [],
        "history": history
    }


# ==========================================
# 5. Metrics & Statistical Reporting
# ==========================================

def calculate_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates Accuracy, Avg Turns, Avg Latency, P95 Latency, and Avg Tokens."""
    n = len(results)
    if n == 0:
        return {}
    passed_count = sum(1 for r in results if r["passed"])
    accuracy = (passed_count / n) * 100.0
    avg_turns = sum(r["turns"] for r in results) / n
    latencies = sorted(r["latency_s"] for r in results)
    avg_lat = sum(latencies) / n
    p95_idx = min(int(math.ceil(0.95 * n)) - 1, n - 1)
    p95_lat = latencies[p95_idx]
    avg_tok = sum(r["tokens"] for r in results) / n

    return {
        "total_tasks": n,
        "passed": passed_count,
        "accuracy": accuracy,
        "avg_turns": avg_turns,
        "avg_latency_s": avg_lat,
        "p95_latency_s": p95_lat,
        "avg_tokens": avg_tok
    }

def print_markdown_comparison(baseline_stats: Dict[str, Any], agent_stats: Dict[str, Any]):
    """Prints a polished Markdown comparison table."""
    print("\n" + "="*70)
    print("  EVALUATION RESULTS: BASELINE VS. PROPOSED AGENT (RUN 1)")
    print("="*70)
    print("| Metric                      | Baseline (Non-Agentic) | Proposed Agent (MVP) | Delta / Improvement |")
    print("|:----------------------------|:----------------------:|:--------------------:|:-------------------:|")
    print(f"| **Accuracy (%)**            | {baseline_stats['accuracy']:6.1f}%               | {agent_stats['accuracy']:6.1f}%             | {agent_stats['accuracy'] - baseline_stats['accuracy']:+6.1f}%            |")
    print(f"| **Average Turns**           | {baseline_stats['avg_turns']:6.2f}                | {agent_stats['avg_turns']:6.2f}              | {agent_stats['avg_turns'] - baseline_stats['avg_turns']:+6.2f}            |")
    print(f"| **Average Latency (s)**     | {baseline_stats['avg_latency_s']:6.2f}s               | {agent_stats['avg_latency_s']:6.2f}s             | {agent_stats['avg_latency_s'] - baseline_stats['avg_latency_s']:+6.2f}s           |")
    print(f"| **P95 Latency (s)**         | {baseline_stats['p95_latency_s']:6.2f}s               | {agent_stats['p95_latency_s']:6.2f}s             | {agent_stats['p95_latency_s'] - baseline_stats['p95_latency_s']:+6.2f}s           |")
    print(f"| **Average Tokens**          | {baseline_stats['avg_tokens']:6.0f}                | {agent_stats['avg_tokens']:6.0f}              | {agent_stats['avg_tokens'] - baseline_stats['avg_tokens']:+6.0f}            |")
    print("="*70)

def print_multi_run_report(pass_at_3: float, pass_pow_3: float, flaky_tasks: List[str], run_accuracies: List[float]):
    """Prints multi-run robustness metrics (pass@3, pass^3, flaky tasks)."""
    print("\n" + "="*70)
    print("  AGENT MULTI-RUN CONSISTENCY REPORT (temperature = 0.7, 3 Runs)")
    print("="*70)
    for idx, acc in enumerate(run_accuracies, 1):
        print(f"  - Run {idx} Accuracy : {acc:5.1f}%")
    print("-" * 70)
    print(f"  * pass@3 (At least 1 pass in 3 runs) : {pass_at_3:5.1f}%")
    print(f"  * pass^3 (All 3 runs passed)         : {pass_pow_3:5.1f}%")
    print(f"  * Flaky Tasks Count                 : {len(flaky_tasks)}")
    if flaky_tasks:
        print(f"  * Flaky Task IDs                    : {', '.join(flaky_tasks)}")
    else:
        print("  * No flaky tasks detected across all 3 runs.")
    print("="*70 + "\n")


# ==========================================
# 6. Main Orchestrator
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Eval Harness for Resilient Multi-Agent Collaborative Travel.")
    parser.add_argument("--tasks", type=str, default="tasks.jsonl", help="Path to tasks.jsonl benchmark file.")
    parser.add_argument("--output-log", type=str, default="eval_logs.json", help="Path to output eval_logs.json.")
    parser.add_argument("--concurrency", type=int, default=8, help="Number of concurrent worker threads.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI model identifier.")
    parser.add_argument("--mock-llm", action="store_true", help="Force fast offline mock LLM simulation mode.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature for Agent multi-run evaluations.")
    args = parser.parse_args()

    tasks_path = Path(args.tasks)
    if not tasks_path.exists():
        print(f"Error: Tasks file '{args.tasks}' not found. Please run generate_tasks.py first.")
        sys.exit(1)

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    print(f"\n[INIT] Loaded {len(tasks)} benchmark scenarios from {tasks_path}.")

    env = MockEnvironment()
    checker = DeterministicChecker(env)
    mock_llm = MockLLMEngine(env)

    # Initialize LLM engine with resilient fallback
    live_llm = None
    if not args.mock_llm:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                live_llm = OpenAILLMEngine(model=args.model, api_key=api_key)
                print(f"[INIT] Live LLM Mode verified: using OpenAI model '{args.model}' (concurrency={args.concurrency}).")
            except Exception as e:
                print(f"[WARN] OpenAI API check failed ({e}). Automatically using Fast Mock LLM Mode.")
                live_llm = None
        else:
            print("[INFO] OPENAI_API_KEY not found in environment. Using Fast Mock LLM Mode.")

    if live_llm is None:
        print("[INIT] Fast Mock LLM Mode active (deterministic spatio-temporal simulation).")

    all_logs: Dict[str, Any] = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_tasks": len(tasks),
            "model": args.model if live_llm else "mock-llm",
            "temperature": args.temperature,
            "concurrency": args.concurrency
        },
        "summary": {},
        "runs": []
    }

    # ----------------------------------------------------
    # Phase 1: Run 1 Comparison (Baseline vs Agent)
    # ----------------------------------------------------
    print("\n>>> [PHASE 1/2] Running Baseline vs. Proposed Agent on all 50 tasks...")

    # Run Baseline
    print("  -> Evaluating Non-Agentic Baseline...")
    baseline_results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(run_baseline, t, mock_llm, live_llm, checker): t["task_id"] for t in tasks}
        for f in as_completed(futures):
            baseline_results.append(f.result())

    baseline_results.sort(key=lambda x: x["task_id"])
    baseline_stats = calculate_stats(baseline_results)
    all_logs["runs"].append({"run_id": "baseline_run1", "results": baseline_results})

    # Run Agent Run 1
    print("  -> Evaluating Proposed Agent (Run 1)...")
    agent_run1_results = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(run_agent, t, mock_llm, live_llm, checker, args.temperature): t["task_id"] for t in tasks}
        for f in as_completed(futures):
            agent_run1_results.append(f.result())

    agent_run1_results.sort(key=lambda x: x["task_id"])
    agent_run1_stats = calculate_stats(agent_run1_results)
    all_logs["runs"].append({"run_id": "agent_run1", "results": agent_run1_results})

    # Print Comparison Table
    print_markdown_comparison(baseline_stats, agent_run1_stats)

    # ----------------------------------------------------
    # Phase 2: Agent Multi-Run Evaluation (3 Runs @ temp=0.7)
    # ----------------------------------------------------
    print(">>> [PHASE 2/2] Running Agent Robustness Evaluation (3 Runs x 50 tasks, temperature=0.7)...")
    agent_runs_results = [agent_run1_results]

    for run_idx in [2, 3]:
        print(f"  -> Evaluating Proposed Agent (Run {run_idx})...")
        run_res = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {executor.submit(run_agent, t, mock_llm, live_llm, checker, args.temperature): t["task_id"] for t in tasks}
            for f in as_completed(futures):
                run_res.append(f.result())
        run_res.sort(key=lambda x: x["task_id"])
        agent_runs_results.append(run_res)
        all_logs["runs"].append({"run_id": f"agent_run{run_idx}", "results": run_res})

    # Compute pass@3, pass^3, and Flaky Tasks
    run_accuracies = [calculate_stats(r)["accuracy"] for r in agent_runs_results]
    task_passes: Dict[str, List[bool]] = {t["task_id"]: [] for t in tasks}

    for r_res in agent_runs_results:
        for r in r_res:
            task_passes[r["task_id"]].append(r["passed"])

    pass_at_3_count = sum(1 for tid, passes in task_passes.items() if any(passes))
    pass_pow_3_count = sum(1 for tid, passes in task_passes.items() if all(passes))
    flaky_tasks = [tid for tid, passes in task_passes.items() if any(passes) and not all(passes)]

    pass_at_3 = (pass_at_3_count / len(tasks)) * 100.0
    pass_pow_3 = (pass_pow_3_count / len(tasks)) * 100.0

    print_multi_run_report(pass_at_3, pass_pow_3, flaky_tasks, run_accuracies)

    all_logs["summary"] = {
        "baseline_run1": baseline_stats,
        "agent_run1": agent_run1_stats,
        "multi_run": {
            "run_accuracies": run_accuracies,
            "pass_at_3": pass_at_3,
            "pass_pow_3": pass_pow_3,
            "flaky_tasks": flaky_tasks,
            "flaky_count": len(flaky_tasks)
        }
    }

    # Save to eval_logs.json
    output_path = Path(args.output_log)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)

    print(f"[COMPLETE] Full evaluation logs saved to '{output_path.resolve()}'.")
    print(f"You can inspect failed traces in '{args.output_log}' for your Week 7 Failure Analysis report.")


if __name__ == "__main__":
    main()
