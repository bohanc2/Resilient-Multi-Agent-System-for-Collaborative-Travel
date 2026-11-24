"""Brute-force reference solver. Used offline and by the API engine to synthesize multi-day collaborative itineraries."""
from __future__ import annotations

from .checker import check_plan
from .data import rainy_hours, to_hhmm, to_min, travel_minutes, venues_for
from .venues_live import get_city_metadata

MAX_FREE = 6


def _groupings(travelers):
    names = [t["name"] for t in travelers]
    if len(travelers) <= 1:
        yield [names]
        return

    # Check if travelers have differing interests or walking abilities or budgets
    differing_interests = len({(t.get("interests") or ["-"])[0] for t in travelers}) > 1
    differing_walk = len({t.get("max_walk", 2) for t in travelers}) > 1
    differing_budget = len({t.get("budget", 2000) for t in travelers}) > 1

    if differing_interests or differing_walk or differing_budget:
        # 1. Group by primary interest
        by_interest: dict[str, list[str]] = {}
        for t in travelers:
            key = (t.get("interests") or ["general"])[0]
            by_interest.setdefault(key, []).append(t["name"])
        if len(by_interest) > 1:
            yield list(by_interest.values())

        # 2. Group by walking limit
        by_walk: dict[int, list[str]] = {}
        for t in travelers:
            w = t.get("max_walk", 2)
            by_walk.setdefault(w, []).append(t["name"])
        if len(by_walk) > 1 and list(by_walk.values()) != list(by_interest.values()):
            yield list(by_walk.values())

        # 3. Multi-group partitions (e.g. 2 or 3 distinct sub-groups) for 4+ travelers
        if len(names) >= 4:
            mid = len(names) // 2
            yield [names[:mid], names[mid:]]
        if len(names) == 6:
            yield [names[:2], names[2:4], names[4:]]

        # 4. Individual tracks if 2-3 travelers
        if 1 < len(names) <= 3:
            yield [[n] for n in names]

    # Finally fallback: all together
    yield [names]


def sanitize_setup(setup: dict, venues: dict) -> dict:
    """Ensure start_location and anchors belong to the current city's venues and enforce standard 09:30-21:00 schedule."""
    setup = dict(setup)
    city = setup.get("city", "taipei").lower().strip()

    # Enrich with geocoded display name if available
    meta = get_city_metadata(city)
    if meta:
        setup["city_display"] = meta["city"]
        setup["center"] = [meta["lat"], meta["lon"]]

    # Standard daily schedule window: 09:30 to 21:00
    setup["day_start"] = "09:30"
    setup["day_end"] = "21:00"

    # 1. Sanitize start_location
    start_loc = setup.get("start_location")
    if not start_loc or start_loc not in venues:
        from .cities import CITY_INFO
        if city in CITY_INFO and CITY_INFO[city]["hotel"] in venues:
            setup["start_location"] = CITY_INFO[city]["hotel"]
        else:
            hotels = [vid for vid, v in venues.items() if "hotel" in v.get("tags", []) or "lodging" in v.get("tags", [])]
            if hotels:
                setup["start_location"] = hotels[0]
            elif venues:
                setup["start_location"] = next(iter(venues.keys()))
            else:
                setup["start_location"] = "hotel_ximen" if city == "taipei" else f"{city}_hotel"

    # 2. Sanitize anchors
    if "anchors" in setup:
        sanitized_anchors = []
        from .cities import CITY_INFO
        city_dinner = CITY_INFO.get(city, {}).get("dinner")

        dining_candidates = [
            vid for vid, v in venues.items()
            if any(t in v.get("tags", []) for t in ["food", "restaurant", "dining", "cafe"])
            and vid != setup["start_location"]
        ]
        if not dining_candidates:
            dining_candidates = [vid for vid in venues if vid != setup["start_location"]]

        for idx, a in enumerate(setup["anchors"]):
            a_copy = dict(a)
            vid = a_copy.get("venue_id")
            if not vid or vid not in venues:
                if city_dinner and city_dinner in venues:
                    replacement_vid = city_dinner
                elif dining_candidates:
                    replacement_vid = dining_candidates[idx % len(dining_candidates)]
                elif venues:
                    replacement_vid = next(iter(venues.keys()))
                else:
                    replacement_vid = ""
                a_copy["venue_id"] = replacement_vid
            sanitized_anchors.append(a_copy)
        setup["anchors"] = sanitized_anchors

    # 3. Sanitize must_visit and preserve_venues
    if "requirements" in setup:
        req = dict(setup["requirements"])
        if "must_visit" in req:
            req["must_visit"] = [vid for vid in req["must_visit"] if vid in venues]
        if "preserve_venues" in req:
            req["preserve_venues"] = [p for p in req["preserve_venues"] if p.get("venue_id") in venues]
        setup["requirements"] = req

    # 4. Currency / budget auto-scaling guard for cross-city requests
    from .cities import CITY_INFO
    if city in CITY_INFO and "travelers" in setup:
        factor = CITY_INFO[city]["budget_factor"]
        if city == "tokyo" and any(t.get("budget", 0) < 3000 for t in setup["travelers"]):
            for t in setup["travelers"]:
                if t.get("budget", 0) < 3000:
                    t["budget"] = int(t.get("budget", 2000) * factor)
        elif city in ("paris", "nyc", "seattle") and any(t.get("budget", 0) > 500 for t in setup["travelers"]):
            for t in setup["travelers"]:
                if t.get("budget", 0) > 500:
                    t["budget"] = max(100, int(t.get("budget", 2000) * factor))

    return setup


def snap_15_ceil(m: int) -> int:
    """Round minutes UP to the nearest 15-minute increment."""
    return ((m + 14) // 15) * 15


def snap_15_round(m: int) -> int:
    """Round minutes to the nearest 15-minute increment."""
    return round(m / 15.0) * 15


def _solve_group_with_venues(group, setup, n_groups, venues, day_visited=None):
    if day_visited is None:
        day_visited = {}

    req = setup.get("requirements", {})
    travelers = [t for t in setup["travelers"] if t["name"] in group]
    max_walk = min(t.get("max_walk", 3) for t in travelers) if travelers else 3
    budget = min(t.get("budget", 10**9) for t in travelers) if travelers else 10**9
    rain = rainy_hours(setup)
    wd = setup.get("weekday", "Sat")
    anchors = sorted([a for a in setup.get("anchors", [])
                      if (a.get("members", "all") == "all" or set(a.get("members", [])) & set(group)) and a.get("venue_id") in venues],
                     key=lambda a: to_min(a["start"]))
    dinner_anchor = anchors[0] if anchors else None
    dinner_vid = dinner_anchor["venue_id"] if dinner_anchor else None
    dinner_s = to_min(dinner_anchor["start"]) if dinner_anchor else to_min("18:30")
    dinner_e = to_min(dinner_anchor["end"]) if dinner_anchor else to_min("20:00")

    day_s = to_min(setup.get("day_start", "09:30"))
    day_e = to_min(setup.get("day_end", "21:00"))
    hotel_id = setup.get("start_location")
    if not hotel_id or hotel_id not in venues:
        hotels = [vid for vid, v in venues.items() if "hotel" in v.get("tags", [])]
        hotel_id = hotels[0] if hotels else next(iter(venues.keys()))

    current_cost = 0
    if dinner_anchor:
        current_cost += venues.get(dinner_vid, {}).get("cost", 0)

    def is_ok(vid, s, e):
        v = venues[vid]
        if wd in v.get("closed_days", []) or v.get("walk", 0) > max_walk:
            return False
        if s < to_min(v.get("open", "08:00")) or e > to_min(v.get("close", "22:00")):
            return False
        if not v.get("indoor", True) and any(s < (h + 1) * 60 and e > h * 60 for h in rain):
            return False
        suit = v.get("time_suitability", "any")
        if suit == "daytime" and s >= to_min("18:00"):
            return False
        if suit == "evening" and e <= to_min("17:00"):
            return False
        if current_cost + v.get("cost", 0) > budget:
            return False
        # Cross-track staggered duplicate check
        if vid in day_visited:
            prev_s, prev_e = day_visited[vid]
            # Must match exact same time slot to allow co-visiting / shared card
            if s != prev_s or e != prev_e:
                return False
        return True

    interests = {i for t in travelers for i in t.get("interests", [])}

    def score_venue(vid, pref_tags, target_t):
        v = venues[vid]
        v_tags = set(v.get("tags", []))
        s = 0
        if v_tags & interests:
            s += 50
        if v_tags & pref_tags:
            s += 25
        if current_cost + v.get("cost", 0) <= budget:
            s += 20
        if dinner_vid and target_t >= to_min("15:00"):
            tr_d = travel_minutes(vid, dinner_vid, venues)
            if tr_d <= 20:
                s += 30
        return s

    candidates = [
        vid for vid in venues
        if vid != hotel_id and vid != dinner_vid
        and "hotel" not in venues[vid].get("tags", [])
        and venues[vid].get("walk", 0) <= max_walk
        and wd not in venues[vid].get("closed_days", [])
    ]

    used = set()
    items = []

    # 1. Morning Activity (starts ~09:45-10:00, ends ~11:30)
    curr_t = day_s
    curr_loc = hotel_id
    morn_cands = [vid for vid in candidates if vid not in used and venues[vid].get("time_suitability") != "evening"]
    morn_cands.sort(key=lambda vid: score_venue(vid, {"scenic", "museum", "culture", "trail", "park", "books", "art"}, curr_t), reverse=True)

    for vid in morn_cands:
        tr = travel_minutes(curr_loc, vid, venues)
        s = snap_15_ceil(curr_t + tr)
        s = max(s, snap_15_ceil(to_min(venues[vid].get("open", "09:00"))))
        min_m = venues[vid].get("min_minutes", 60)
        dur = max(min_m, min(105, round(venues[vid].get("duration_mins", 90) / 15) * 15))
        e = s + dur
        if e <= to_min("12:00") and is_ok(vid, s, e):
            items.append({"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e), "members": list(group)})
            used.add(vid)
            current_cost += venues[vid].get("cost", 0)
            curr_loc = vid
            curr_t = e
            break

    # 2. Lunch Activity (starts ~11:45-12:15, ends ~13:00-13:30)
    food_tags = {"food", "lunch", "dining", "restaurant", "cafe", "night_market"}
    lunch_cands = [vid for vid in candidates if vid not in used and (set(venues[vid].get("tags", [])) & food_tags)]
    if not lunch_cands:
        lunch_cands = [vid for vid in candidates if vid not in used]
    lunch_cands.sort(key=lambda vid: score_venue(vid, food_tags | interests, curr_t), reverse=True)

    for vid in lunch_cands:
        tr = travel_minutes(curr_loc, vid, venues)
        s = snap_15_ceil(curr_t + tr)
        s = max(s, to_min("11:30"))
        dur = max(venues[vid].get("min_minutes", 60), 60)
        dur = round(dur / 15) * 15
        e = s + dur
        if e <= to_min("13:45") and is_ok(vid, s, e):
            items.append({"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e), "members": list(group)})
            used.add(vid)
            current_cost += venues[vid].get("cost", 0)
            curr_loc = vid
            curr_t = e
            break

    # 3. Afternoon Continuous Activities (until convergence ~17:15-17:45)
    while True:
        tr_to_din = travel_minutes(curr_loc, dinner_vid, venues) if dinner_vid else 0
        if curr_t + tr_to_din >= to_min("17:15"):
            break

        aft_cands = [vid for vid in candidates if vid not in used and venues[vid].get("time_suitability") != "evening"]
        if not aft_cands:
            break
        aft_cands.sort(key=lambda vid: score_venue(vid, {"museum", "park", "culture", "viewpoint", "shopping", "landmark", "cafe"} | interests, curr_t), reverse=True)

        found = False
        for vid in aft_cands:
            tr = travel_minutes(curr_loc, vid, venues)
            s = snap_15_ceil(curr_t + tr)
            s = max(s, snap_15_ceil(to_min(venues[vid].get("open", "09:00"))))
            min_m = venues[vid].get("min_minutes", 45)
            tr_d = travel_minutes(vid, dinner_vid, venues) if dinner_vid else 0

            # If this stop can reach dinner convergence (~17:50 - 18:05)
            target_arrival = to_min("18:05")
            ideal_end = ((target_arrival - tr_d) // 15) * 15
            close_t = to_min(venues[vid].get("close", "22:00"))
            max_end = min(close_t, max(s + min_m, s + 120), dinner_s - tr_d)

            if s + min_m + tr_d > dinner_s or s + min_m > close_t:
                continue

            if s + min_m + tr_d >= to_min("16:15"):
                if ideal_end >= s + min_m and ideal_end <= max_end:
                    e = ideal_end
                else:
                    dur = max(min_m, min(90, round(venues[vid].get("duration_mins", 75) / 15) * 15))
                    e = min(max_end, s + dur)
            else:
                dur = max(min_m, min(90, round(venues[vid].get("duration_mins", 75) / 15) * 15))
                e = min(max_end, s + dur)

            if e < s + min_m:
                continue

            if e + tr_d <= dinner_s and is_ok(vid, s, e):
                items.append({"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e), "members": list(group)})
                used.add(vid)
                current_cost += venues[vid].get("cost", 0)
                curr_loc = vid
                curr_t = e
                found = True
                break

        if not found:
            break

    # If the group still arrives earlier than 17:50 (due to short activity or early finish),
    # stretch the last activity up to its close time or max 135 min so arrival aligns with other groups!
    if items and items[-1].get("venue_id") != dinner_vid and dinner_vid:
        last_item = items[-1]
        last_vid = last_item["venue_id"]
        last_s = to_min(last_item["start"])
        last_e = to_min(last_item["end"])
        tr_d = travel_minutes(last_vid, dinner_vid, venues)
        arrival = last_e + tr_d
        if arrival < to_min("17:50"):
            target_arrival = to_min("18:05")
            ideal_end = ((target_arrival - tr_d) // 15) * 15
            close_t = to_min(venues[last_vid].get("close", "22:00"))
            new_end = ((min(ideal_end, close_t, last_s + 135, dinner_s - tr_d)) // 15) * 15
            if new_end >= last_s + venues[last_vid].get("min_minutes", 30) and new_end <= close_t:
                last_item["end"] = to_hhmm(new_end)
                curr_loc = last_vid
                curr_t = new_end

    # 4. Dinner Anchor (18:30 to 20:00)
    if dinner_anchor:
        items.append({
            "venue_id": dinner_vid,
            "start": to_hhmm(dinner_s),
            "end": to_hhmm(dinner_e),
            "members": list(group),
            "anchor": True,
            "is_shared": True
        })
        curr_loc = dinner_vid
        curr_t = dinner_e

    # 5. Post-Dinner Evening Activity (20:15 to 21:00)
    eve_cands = [vid for vid in candidates if vid not in used and venues[vid].get("time_suitability") in ("evening", "any")]
    eve_cands.sort(key=lambda vid: score_venue(vid, {"viewpoint", "night_market", "dessert", "bar", "scenic"} | interests, curr_t), reverse=True)

    for vid in eve_cands:
        tr = travel_minutes(curr_loc, vid, venues)
        s = snap_15_ceil(curr_t + tr)
        min_m = venues[vid].get("min_minutes", 45)
        dur = max(min_m, 45)
        dur = round(dur / 15) * 15
        e = s + dur
        close_t = to_min(venues[vid].get("close", "22:00"))
        if e <= min(close_t, day_e) and is_ok(vid, s, e):
            items.append({"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e), "members": list(group)})
            used.add(vid)
            break

    return items


def merge_identical_traveler_tracks(itinerary: list[dict], travelers: list[dict]) -> list[dict]:
    """If two or more travelers have the identical sequence of stops and times, merge their items."""
    traveler_names = [t["name"] for t in travelers]
    if len(traveler_names) <= 1:
        return itinerary

    days = sorted(list({it.get("day", 1) for it in itinerary})) or [1]
    merged_all = []

    for d in days:
        day_items = [it for it in itinerary if it.get("day", 1) == d]

        # Build sequence for each traveler on this day
        sched_by_traveler = {}
        for name in traveler_names:
            stops = tuple(
                (it["venue_id"], it["start"], it["end"])
                for it in sorted(day_items, key=lambda x: to_min(x["start"]))
                if name in it.get("members", [])
            )
            sched_by_traveler[name] = stops

        # Find equivalence classes of travelers with identical non-empty schedules
        from collections import defaultdict
        groups = defaultdict(list)
        for name, stops in sched_by_traveler.items():
            if stops:
                groups[stops].append(name)

        # For each group of travelers with identical schedules, ensure their items are unified
        unified_day_items = []
        for it in day_items:
            it_copy = dict(it)
            it_members = set(it_copy.get("members", []))
            for stops, group_names in groups.items():
                if len(group_names) > 1 and it_members & set(group_names):
                    it_members.update(group_names)
            it_copy["members"] = sorted(list(it_members))
            unified_day_items.append(it_copy)

        merged_all.extend(deduplicate_itinerary(unified_day_items, len(traveler_names)))

    return merged_all


def deduplicate_itinerary(itinerary: list[dict], total_travelers: int = 0) -> list[dict]:
    """Merge items having identical (day, venue_id, start, end), combining member lists into a single shared stop."""
    merged: dict[tuple[int, str, str, str], dict] = {}
    order: list[tuple[int, str, str, str]] = []
    for it in itinerary:
        day = it.get("day", 1)
        key = (day, it["venue_id"], it["start"], it["end"])
        if key not in merged:
            merged[key] = dict(it)
            merged[key]["day"] = day
            merged[key]["members"] = list(it.get("members", []))
            order.append(key)
        else:
            m = set(merged[key]["members"])
            m.update(it.get("members", []))
            merged[key]["members"] = sorted(list(m))
            if it.get("is_shared") or merged[key].get("is_shared"):
                merged[key]["is_shared"] = True

    # Mark is_shared if all travelers are present or venue is an evening dinner / convergence anchor
    for key in order:
        item = merged[key]
        if total_travelers > 0 and len(item["members"]) >= total_travelers:
            item["is_shared"] = True
        elif item.get("start", "") >= "18:00" and any(tag in item.get("venue_id", "") for tag in ["dinner", "market", "101"]):
            item["is_shared"] = True
    return [merged[k] for k in order]


def solve(setup: dict):
    """Return a valid multi-day or single-day plan with transit times, or None."""
    venues = venues_for(setup)
    if not venues or len(venues) < 3:
        return None

    setup = sanitize_setup(setup, venues)
    total_days = max(1, min(5, int(setup.get("duration_days", setup.get("days", 2)))))
    total_travelers = len(setup.get("travelers", []))
    used_across_days: set[str] = set()
    all_day_itineraries: list[dict] = []

    for day in range(1, total_days + 1):
        day_setup = dict(setup)
        day_setup["day_start"] = "09:30"
        day_setup["day_end"] = "21:00"

        # Exclude venues visited on earlier days to guarantee diverse, non-repeating recommendations
        avail_venues = {
            vid: v for vid, v in venues.items()
            if vid not in used_across_days or "hotel" in v.get("tags", []) or vid == setup.get("start_location")
        }
        non_hotel_avail = [vid for vid in avail_venues if "hotel" not in avail_venues[vid].get("tags", [])]
        if len(non_hotel_avail) < 3:
            avail_venues = venues

        # Day anchors: on Day 1, use setup anchors if present.
        # If no setup anchors on Day 1 and single traveler, allow free activities without forcing a dinner anchor.
        # For multiplayer group trips (2+ travelers) or Day 2+, provide evening convergence dinner.
        if day == 1 and setup.get("anchors"):
            day_anchors = list(setup.get("anchors", []))
            for a in day_anchors:
                a["is_shared"] = True
        elif day == 1 and not setup.get("anchors") and len(setup.get("travelers", [])) < 2:
            day_anchors = []
        else:
            # Convergence dinner must be suitable for all group members (walk limit, indoor/evening)
            max_group_walk = min(t.get("max_walk", 3) for t in setup["travelers"])
            dinner_candidates = [
                vid for vid, v in avail_venues.items()
                if any(t in v.get("tags", []) for t in ["dining", "food", "restaurant", "cafe", "night_market"])
                and v.get("walk", 0) <= max_group_walk
                and not any(tag in v.get("tags", []) for tag in ["hiking", "trail", "mountain"])
                and vid != setup.get("start_location")
            ]
            if not dinner_candidates:
                # If all food spots were used on earlier days, allow venues from the full city venue pool
                dinner_candidates = [
                    vid for vid, v in venues.items()
                    if any(t in v.get("tags", []) for t in ["dining", "food", "restaurant", "cafe", "night_market"])
                    and v.get("walk", 0) <= max_group_walk
                    and not any(tag in v.get("tags", []) for tag in ["hiking", "trail", "mountain"])
                    and vid != setup.get("start_location")
                ]
            if not dinner_candidates:
                dinner_candidates = [
                    vid for vid, v in venues.items()
                    if v.get("walk", 0) <= max_group_walk
                    and not any(tag in v.get("tags", []) for tag in ["hiking", "trail", "mountain"])
                    and vid != setup.get("start_location")
                ]
            
            from .cities import CITY_INFO
            city_dinner = CITY_INFO.get(setup.get("city", "taipei").lower(), {}).get("dinner")
            if day == 1 and city_dinner and city_dinner in avail_venues:
                chosen_dinner = city_dinner
            else:
                evening_dinners = [vid for vid in dinner_candidates if venues[vid].get("time_suitability") == "evening"]
                chosen_dinner = evening_dinners[0] if evening_dinners else dinner_candidates[0]
            day_anchors = [{
                "venue_id": chosen_dinner,
                "start": "18:30",
                "end": "20:00",
                "members": [t["name"] for t in setup["travelers"]],
                "anchor": True,
                "is_shared": True
            }]
        day_setup["anchors"] = day_anchors

        day_items = None
        for grouping in _groupings(day_setup["travelers"]):
            parts = []
            day_visited = {}
            for g in grouping:
                r = _solve_group_with_venues(g, day_setup, len(grouping), avail_venues, day_visited)
                if r is None:
                    break
                for it in r:
                    day_visited[it["venue_id"]] = (to_min(it["start"]), to_min(it["end"]))
                parts.extend(r)
            else:
                raw_it = [{k: v for k, v in it.items() if k != "anchor"} for it in parts]
                merged_tracks = merge_identical_traveler_tracks(raw_it, day_setup["travelers"])
                day_items = deduplicate_itinerary(merged_tracks, total_travelers)
                break

        # Fallback relaxation if strict grouping had no solution
        if not day_items:
            relaxed_setup = dict(day_setup)
            relaxed_setup["requirements"] = {**relaxed_setup.get("requirements", {}), "min_activities": 1}
            for grouping in _groupings(relaxed_setup["travelers"]):
                parts = []
                day_visited = {}
                for g in grouping:
                    r = _solve_group_with_venues(g, relaxed_setup, len(grouping), venues, day_visited)
                    if r is None:
                        break
                    for it in r:
                        day_visited[it["venue_id"]] = (to_min(it["start"]), to_min(it["end"]))
                    parts.extend(r)
                else:
                    raw_it = [{k: v for k, v in it.items() if k != "anchor"} for it in parts]
                    merged_tracks = merge_identical_traveler_tracks(raw_it, day_setup["travelers"])
                    day_items = deduplicate_itinerary(merged_tracks, total_travelers)
                    break

        if day_items:
            for it in day_items:
                it["day"] = day
                if "hotel" not in it["venue_id"]:
                    used_across_days.add(it["venue_id"])
            all_day_itineraries.extend(day_items)

    if not all_day_itineraries:
        return None

    # Sort all day itineraries chronologically by (day, start_time)
    all_day_itineraries.sort(key=lambda x: (x.get("day", 1), to_min(x["start"])))

    # Calculate transit_from_prev for every item per day
    hotel_id = setup.get("start_location")
    hotel_name = venues.get(hotel_id, {}).get("name", "Hotel Departure")

    for day in range(1, total_days + 1):
        day_items = [it for it in all_day_itineraries if it.get("day") == day]
        day_items.sort(key=lambda x: to_min(x["start"]))
        member_last_loc = {t["name"]: (hotel_id, "09:30") for t in setup["travelers"]}

        for it in day_items:
            prev_vids = [member_last_loc.get(m, (hotel_id, "09:30"))[0] for m in it["members"]]
            prev_vid = prev_vids[0] if prev_vids else hotel_id
            tr_mins = travel_minutes(prev_vid, it["venue_id"], venues)
            va = venues.get(prev_vid, {})
            vb = venues.get(it["venue_id"], {})

            # Distance in km for realistic transit mode estimation
            d_km = 1.0
            if va.get("lat") and vb.get("lat"):
                import math
                lat1, lon1, lat2, lon2 = map(math.radians, (va["lat"], va["lon"], vb["lat"], vb["lon"]))
                d_km = 2 * 6371 * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2) ** 2 +
                                                      math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))

            # Mode based on distance: ≤ 1.2km -> walk, > 1.2km -> transit/drive
            if d_km <= 1.2 or tr_mins <= 12:
                mode = "walk"
            elif d_km <= 10.0 or tr_mins <= 35:
                mode = "transit"
            else:
                mode = "drive"

            prev_name = venues.get(prev_vid, {}).get("name", "Hotel Departure") if prev_vid != hotel_id else hotel_name

            it["transit_from_prev"] = {
                "mode": mode,
                "duration_mins": tr_mins,
                "distance_km": round(d_km, 1),
                "from_venue_id": prev_vid,
                "from_venue_name": prev_name
            }

            for m in it["members"]:
                member_last_loc[m] = (it["venue_id"], it["end"])

    city_disp = setup.get("city_display", setup.get("city", "Taipei").title())
    return {
        "feasible": True,
        "reason": f"Synthesized {total_days}-day collaborative itinerary for {city_disp}",
        "city": city_disp,
        "days": total_days,
        "total_days": total_days,
        "duration_days": total_days,
        "itinerary": all_day_itineraries
    }
