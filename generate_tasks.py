"""
generate_tasks.py - Generates 50 standardized benchmark tasks for Collaborative Travel.

Benchmark Distribution:
- 44 normal tasks (diverse cities, 2-5 travelers, budgets, stamina, split-and-regroup, hard anchors).
- 4 edge cases (sudden rain contingency, venue closure, tight regroup synchronization, rain + budget).
- 2 unanswerable tasks (spatio-temporal transit impossibility, financial impossibility).

Format Guarantee:
Every JSON line strictly contains uniform keys in fixed order:
{
  "task_id": str,
  "category": "normal" | "edge_case" | "unanswerable",
  "city": str,
  "num_travelers": int,
  "travelers": list[dict],
  "prompt": str,
  "constraints": {
    "is_answerable": bool,
    "city": str,
    "hard_anchor": dict,
    "weather_rain_after": str | None,
    "max_regroup_gap_mins": int,
    "max_budget_per_person": int | None,
    "required_regroup_venue": str | None,
    "required_regroup_time": str | None,
    "rejection_reason": str | None
  }
}
"""

import json
from pathlib import Path

tasks = []

cities_data = [
    {
        "city": "Taipei",
        "hard_anchor": {"venue": "Taipei 101 Dining", "start_time": "18:30", "end_time": "20:00"},
        "regroup_time": "18:15",
        "venues_outdoor": ["Elephant Mountain Trail", "Daan Forest Park"],
        "venues_indoor": ["National Palace Museum", "Syntrend Creative Park", "Yongkang Street Cafes", "Taipei Fine Arts Museum"]
    },
    {
        "city": "Tokyo",
        "hard_anchor": {"venue": "Roppongi Hills Sky Deck", "start_time": "18:30", "end_time": "20:00"},
        "regroup_time": "18:15",
        "venues_outdoor": ["Meiji Shrine & Yoyogi Park", "Shinjuku Gyoen"],
        "venues_indoor": ["teamLab Planets", "Akihabara Electric Town", "Tokyo National Museum", "Ginza Luxury Dining"]
    },
    {
        "city": "Seattle",
        "hard_anchor": {"venue": "Space Needle Observation Deck", "start_time": "18:00", "end_time": "19:30"},
        "regroup_time": "17:45",
        "venues_outdoor": ["Discovery Park Trail", "Kerry Park"],
        "venues_indoor": ["Chihuly Garden and Glass", "Pike Place Market", "Museum of Pop Culture (MoPOP)", "Elliott Bay Book Company"]
    },
    {
        "city": "Kyoto",
        "hard_anchor": {"venue": "Gion Kaiseki Dinner", "start_time": "18:00", "end_time": "20:00"},
        "regroup_time": "17:45",
        "venues_outdoor": ["Fushimi Inari Shrine", "Kiyomizu-dera"],
        "venues_indoor": ["Kyoto Museum of Crafts and Design", "Nishiki Market", "Kyoto Railway Museum"]
    },
    {
        "city": "New York",
        "hard_anchor": {"venue": "Broadway Theatre Show", "start_time": "19:00", "end_time": "21:30"},
        "regroup_time": "18:30",
        "venues_outdoor": ["Central Park Rambles", "High Line & Chelsea Market"],
        "venues_indoor": ["Metropolitan Museum of Art", "One World Observatory", "SoHo Boutique Walk"]
    }
]

traveler_templates = [
    [
        {"name": "Alice", "interests": ["culture", "museums"], "budget": 80, "stamina": "medium"},
        {"name": "Bob", "interests": ["nature", "hiking"], "budget": 60, "stamina": "high"}
    ],
    [
        {"name": "Alice", "interests": ["shopping", "cafes"], "budget": 120, "stamina": "low"},
        {"name": "Bob", "interests": ["hiking", "photography"], "budget": 70, "stamina": "high"},
        {"name": "Charlie", "interests": ["history", "art"], "budget": 90, "stamina": "medium"}
    ],
    [
        {"name": "David", "interests": ["tech", "gadgets"], "budget": 110, "stamina": "medium"},
        {"name": "Emma", "interests": ["sightseeing", "parks"], "budget": 65, "stamina": "high"},
        {"name": "Frank", "interests": ["food", "markets"], "budget": 85, "stamina": "low"},
        {"name": "Grace", "interests": ["modern art"], "budget": 95, "stamina": "medium"}
    ],
    [
        {"name": "Henry", "interests": ["architecture", "views"], "budget": 130, "stamina": "medium"},
        {"name": "Ivy", "interests": ["walking", "nature"], "budget": 50, "stamina": "high"},
        {"name": "Jack", "interests": ["coffee", "books"], "budget": 75, "stamina": "low"},
        {"name": "Kelly", "interests": ["local shopping"], "budget": 100, "stamina": "low"},
        {"name": "Leo", "interests": ["museums", "history"], "budget": 80, "stamina": "medium"}
    ]
]

# 1. 44 Normal Tasks
for i in range(1, 45):
    city_info = cities_data[(i - 1) % len(cities_data)]
    travelers_group = traveler_templates[(i - 1) % len(traveler_templates)]
    num_travelers = len(travelers_group)
    traveler_names = ", ".join([t["name"] for t in travelers_group])
    interests_summary = "; ".join([f"{t['name']} prefers {', '.join(t['interests'])} (budget ${t['budget']}, stamina {t['stamina']})" for t in travelers_group])
    min_budget = min(t["budget"] for t in travelers_group)

    prompt = (
        f"Plan a 1-day collaborative travel itinerary in {city_info['city']} for a group of {num_travelers} travelers ({traveler_names}).\n"
        f"Individual traveler limits and preferences: {interests_summary}.\n"
        f"Important fixed booking: All travelers share a mandatory, non-negotiable reservation at {city_info['hard_anchor']['venue']} "
        f"from {city_info['hard_anchor']['start_time']} to {city_info['hard_anchor']['end_time']}.\n"
        f"The travelers wish to split into interest-aligned sub-groups in the afternoon, and must all regroup at "
        f"{city_info['hard_anchor']['venue']} no later than {city_info['regroup_time']}. "
        f"Arrival time difference across all sub-groups must be within 15 minutes. "
        f"Ensure all venue operating hours and transit travel times are strictly respected."
    )

    task = {
        "task_id": f"task_{i:02d}",
        "category": "normal",
        "city": city_info["city"],
        "num_travelers": num_travelers,
        "travelers": travelers_group,
        "prompt": prompt,
        "constraints": {
            "is_answerable": True,
            "city": city_info["city"],
            "hard_anchor": city_info["hard_anchor"],
            "weather_rain_after": None,
            "max_regroup_gap_mins": 15,
            "max_budget_per_person": min_budget,
            "required_regroup_venue": city_info["hard_anchor"]["venue"],
            "required_regroup_time": city_info["regroup_time"],
            "rejection_reason": None
        }
    }
    tasks.append(task)

# 2. 4 Edge Cases
# Edge 1: Sudden afternoon downpour in Taipei
edge_1 = {
    "task_id": "task_45_edge_rain_taipei",
    "category": "edge_case",
    "city": "Taipei",
    "num_travelers": 3,
    "travelers": [
        {"name": "Alice", "interests": ["cafes", "tea"], "budget": 90, "stamina": "low"},
        {"name": "Bob", "interests": ["hiking", "views"], "budget": 70, "stamina": "high"},
        {"name": "Charlie", "interests": ["shopping", "tech"], "budget": 100, "stamina": "medium"}
    ],
    "prompt": (
        "Plan a 1-day collaborative itinerary in Taipei for Alice, Bob, and Charlie.\n"
        "Preferences: Bob wants an afternoon outdoor hike, Alice wants cafes, and Charlie wants tech shopping.\n"
        "Fixed Booking: Dinner reservation at Taipei 101 Dining from 18:30 to 20:00.\n"
        "CONTINGENCY ALERT: Live weather forecast predicts an 85% rain probability starting at 14:00.\n"
        "Requirements: Do not schedule outdoor activities after 14:00. If Bob planned an afternoon hike, "
        "repair that segment with a nearby indoor alternative. All sub-groups must regroup at Taipei 101 Dining by 18:15 "
        "with an arrival gap of <= 15 minutes. Fixed dinner cannot be moved."
    ),
    "constraints": {
        "is_answerable": True,
        "city": "Taipei",
        "hard_anchor": {"venue": "Taipei 101 Dining", "start_time": "18:30", "end_time": "20:00"},
        "weather_rain_after": "14:00",
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": 70,
        "required_regroup_venue": "Taipei 101 Dining",
        "required_regroup_time": "18:15",
        "rejection_reason": None
    }
}
tasks.append(edge_1)

# Edge 2: Venue closure in Tokyo
edge_2 = {
    "task_id": "task_46_edge_closed_tokyo",
    "category": "edge_case",
    "city": "Tokyo",
    "num_travelers": 2,
    "travelers": [
        {"name": "Kenji", "interests": ["modern art", "museums"], "budget": 80, "stamina": "medium"},
        {"name": "Yuki", "interests": ["electronics", "gaming"], "budget": 90, "stamina": "medium"}
    ],
    "prompt": (
        "Plan a collaborative afternoon in Tokyo for Kenji and Yuki.\n"
        "Kenji specifically requested visiting Mori Art Museum, while Yuki wants to explore Akihabara Electric Town.\n"
        "Fixed Booking: Roppongi Hills Sky Deck sunset reservation from 18:30 to 20:00.\n"
        "VENUE ALERT: Check venue status via tools. Mori Art Museum is currently closed today for emergency maintenance.\n"
        "Requirements: Detect the closure, replace Mori Art Museum with a valid open indoor art alternative (such as teamLab Planets or Tokyo National Museum), "
        "and synchronize both travelers to regroup at Roppongi Hills Sky Deck by 18:15 (gap <= 15 mins)."
    ),
    "constraints": {
        "is_answerable": True,
        "city": "Tokyo",
        "hard_anchor": {"venue": "Roppongi Hills Sky Deck", "start_time": "18:30", "end_time": "20:00"},
        "weather_rain_after": None,
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": 80,
        "required_regroup_venue": "Roppongi Hills Sky Deck",
        "required_regroup_time": "18:15",
        "rejection_reason": None
    }
}
tasks.append(edge_2)

# Edge 3: Tight split & regroup synchronization in Seattle
edge_3 = {
    "task_id": "task_47_edge_tight_regroup_seattle",
    "category": "edge_case",
    "city": "Seattle",
    "num_travelers": 4,
    "travelers": [
        {"name": "Sam", "interests": ["hiking"], "budget": 60, "stamina": "high"},
        {"name": "Alex", "interests": ["nature"], "budget": 60, "stamina": "high"},
        {"name": "Taylor", "interests": ["craft market"], "budget": 80, "stamina": "low"},
        {"name": "Jordan", "interests": ["food tasting"], "budget": 85, "stamina": "low"}
    ],
    "prompt": (
        "Plan an afternoon trip in Seattle for Sam, Alex, Taylor, and Jordan.\n"
        "Group 1 (Sam & Alex) heads to Discovery Park Trail (transit time to Space Needle: 30 mins).\n"
        "Group 2 (Taylor & Jordan) visits Pike Place Market (transit time to Space Needle: 15 mins).\n"
        "Fixed Booking: Space Needle Observation Deck at 18:00 to 19:30.\n"
        "SYNCHRONIZATION CONSTRAINT: Both groups must regroup at the Space Needle at 17:45. "
        "Their arrival times must not differ by more than 10 minutes (strictly <= 15 mins). "
        "Because Group 1 has a longer transit time, their departure time must be precisely offset from Group 2's departure time."
    ),
    "constraints": {
        "is_answerable": True,
        "city": "Seattle",
        "hard_anchor": {"venue": "Space Needle Observation Deck", "start_time": "18:00", "end_time": "19:30"},
        "weather_rain_after": None,
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": 60,
        "required_regroup_venue": "Space Needle Observation Deck",
        "required_regroup_time": "17:45",
        "rejection_reason": None
    }
}
tasks.append(edge_3)

# Edge 4: Rain forecast + tight budget in Kyoto
edge_4 = {
    "task_id": "task_48_edge_rain_budget_kyoto",
    "category": "edge_case",
    "city": "Kyoto",
    "num_travelers": 3,
    "travelers": [
        {"name": "Hana", "interests": ["shrine hiking"], "budget": 25, "stamina": "high"},
        {"name": "Ren", "interests": ["traditional crafts"], "budget": 30, "stamina": "medium"},
        {"name": "Aoi", "interests": ["street food"], "budget": 35, "stamina": "low"}
    ],
    "prompt": (
        "Plan an afternoon in Kyoto for Hana, Ren, and Aoi with a strict low-cost constraint.\n"
        "Hana originally planned to hike Fushimi Inari Shrine (outdoor), while Ren and Aoi visit Nishiki Market.\n"
        "Fixed Booking: Gion Kaiseki Dinner at 18:00 to 20:00 (pre-paid voucher, not counted against afternoon budget).\n"
        "CONTINGENCY & BUDGET ALERT: Rain starts at 13:00. Hana's outdoor hike must be replaced with an indoor venue, "
        "BUT Hana's afternoon budget is strictly capped at $25. "
        "Check venue admission costs: replace the outdoor hike with an affordable indoor venue (e.g. Kyoto Museum of Crafts and Design at $8 or Railway Museum at $12), "
        "and synchronize regrouping at Gion Kaiseki Dinner at 17:45 (gap <= 15 mins)."
    ),
    "constraints": {
        "is_answerable": True,
        "city": "Kyoto",
        "hard_anchor": {"venue": "Gion Kaiseki Dinner", "start_time": "18:00", "end_time": "20:00"},
        "weather_rain_after": "13:00",
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": 25,
        "required_regroup_venue": "Gion Kaiseki Dinner",
        "required_regroup_time": "17:45",
        "rejection_reason": None
    }
}
tasks.append(edge_4)

# 3. 2 Unanswerable Cases
# Unanswerable 1: Physical transit impossibility
unans_1 = {
    "task_id": "task_49_unanswerable_physics",
    "category": "unanswerable",
    "city": "Taipei / Kaohsiung",
    "num_travelers": 2,
    "travelers": [
        {"name": "Mia", "interests": ["skyscrapers"], "budget": 100, "stamina": "medium"},
        {"name": "Noah", "interests": ["seafood"], "budget": 100, "stamina": "medium"}
    ],
    "prompt": (
        "Plan an afternoon schedule for Mia and Noah.\n"
        "Mia insists on finishing a tour at Taipei 101 Observation Deck ending at 17:00.\n"
        "Fixed Booking: A mandatory family dinner reservation at Kaohsiung Harbor Dinner in Kaohsiung at 17:15.\n"
        "Transit constraint: Distance between Taipei and Kaohsiung exceeds 300 km, requiring at least 110 minutes by High-Speed Rail.\n"
        "Requirement: If it is physically impossible to travel from Taipei 101 to Kaohsiung within 15 minutes, "
        "you must explicitly REJECT this request and explain the spatio-temporal conflict."
    ),
    "constraints": {
        "is_answerable": False,
        "city": "Taipei / Kaohsiung",
        "hard_anchor": {"venue": "Kaohsiung Harbor Dinner", "start_time": "17:15", "end_time": "19:00"},
        "weather_rain_after": None,
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": None,
        "required_regroup_venue": "Kaohsiung Harbor Dinner",
        "required_regroup_time": "17:15",
        "rejection_reason": "Physical transit impossibility: Taipei to Kaohsiung takes >= 110 minutes, impossible to travel within 15 minutes."
    }
}
tasks.append(unans_1)

# Unanswerable 2: Budget impossibility
unans_2 = {
    "task_id": "task_50_unanswerable_budget",
    "category": "unanswerable",
    "city": "Tokyo",
    "num_travelers": 2,
    "travelers": [
        {"name": "Leo", "interests": ["fine dining"], "budget": 0, "stamina": "low"},
        {"name": "Maya", "interests": ["luxury sushi"], "budget": 0, "stamina": "low"}
    ],
    "prompt": (
        "Plan an evening itinerary in Tokyo for Leo and Maya.\n"
        "Budget constraint: Both travelers have a strict, absolute budget of $0 total (zero spending allowed).\n"
        "Mandatory requirement: The itinerary MUST book and include dinner at Sushi Yoshitake (3-star Michelin, minimum $350 per person).\n"
        "Requirement: If it is financially impossible to book Sushi Yoshitake ($350/person) with a $0 budget, "
        "you must explicitly REJECT this request and explain the financial impossibility."
    ),
    "constraints": {
        "is_answerable": False,
        "city": "Tokyo",
        "hard_anchor": {"venue": "Sushi Yoshitake", "start_time": "18:00", "end_time": "20:00"},
        "weather_rain_after": None,
        "max_regroup_gap_mins": 15,
        "max_budget_per_person": 0,
        "required_regroup_venue": "Sushi Yoshitake",
        "required_regroup_time": "18:00",
        "rejection_reason": "Financial impossibility: Sushi Yoshitake requires $350/person but traveler budget is $0."
    }
}
tasks.append(unans_2)

# Write to tasks.jsonl
output_path = Path("tasks.jsonl")
with open(output_path, "w", encoding="utf-8") as f:
    for task in tasks:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")

print(f"Successfully generated {len(tasks)} tasks in {output_path.resolve()}:")
print(f"- Normal tasks: {sum(1 for t in tasks if t['category'] == 'normal')}")
print(f"- Edge case tasks: {sum(1 for t in tasks if t['category'] == 'edge_case')}")
print(f"- Unanswerable tasks: {sum(1 for t in tasks if t['category'] == 'unanswerable')}")
