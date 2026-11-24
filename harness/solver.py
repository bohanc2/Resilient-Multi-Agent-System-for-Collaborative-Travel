"""Brute-force reference solver. Used offline and by the API engine to synthesize multi-day collaborative itineraries."""
from __future__ import annotations

from .checker import check_plan
from .data import rainy_hours, to_hhmm, to_min, travel_minutes, venues_for
from .venues_live import get_city_metadata

MAX_FREE = 4


def _groupings(travelers):
    names = [t["name"] for t in travelers]
    yield [names]
    by_interest: dict[str, list[str]] = {}
    for t in travelers:
        by_interest.setdefault((t.get("interests") or ["-"])[0], []).append(t["name"])
    if len(by_interest) > 1:
        yield list(by_interest.values())
    if len(names) > 1:
        yield [[n] for n in names]


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


def _solve_group_with_venues(group, setup, n_groups, venues):
    req = setup.get("requirements", {})
    travelers = [t for t in setup["travelers"] if t["name"] in group]
    max_walk = min(t.get("max_walk", 3) for t in travelers) if travelers else 3
    rain = rainy_hours(setup)
    wd = setup.get("weekday", "Sat")
    anchors = sorted([a for a in setup.get("anchors", [])
                      if (a.get("members", "all") == "all" or set(a.get("members", [])) & set(group)) and a.get("venue_id") in venues],
                     key=lambda a: to_min(a["start"]))
    anchor_vids = {a["venue_id"] for a in anchors}
    gap = req.get("max_regroup_gap_min")
    must = set(req.get("must_visit", [])) | {p["venue_id"] for p in req.get("preserve_venues", [])
                                             if (p.get("members", "all") == "all" or set(p.get("members", [])) & set(group)) and p.get("venue_id") in venues}
    day_e = to_min(setup.get("day_end", "21:00"))
    min_act = max(1, int(req.get("min_activities", 2)))

    def ok_venue(vid, s, e):
        v = venues[vid]
        if wd in v.get("closed_days", []) or v.get("walk", 0) > max_walk:
            return False
        if s < to_min(v.get("open", "09:00")) or e > to_min(v.get("close", "21:30")):
            return False
        if not v.get("indoor", True) and any(s < (h + 1) * 60 and e > h * 60 for h in rain):
            return False
        return True

    def goal(items):
        free = [it for it in items if not it.get("anchor")]
        if len(free) < min_act:
            return False
        vids = {it["venue_id"] for it in items}
        if not must <= vids:
            return False
        all_city_tags = {tag for v in venues.values() for tag in v.get("tags", [])}
        for t in travelers:
            if req.get("interest_coverage") and t.get("interests"):
                matching_city_interests = set(t["interests"]) & all_city_tags
                if matching_city_interests and not any(set(venues[it["venue_id"]]["tags"]) & matching_city_interests for it in free):
                    return False
            if sum(venues[it["venue_id"]]["cost"] for it in items) > t.get("budget", 10 ** 9):
                return False
        return True

    candidates = [vid for vid in venues if vid not in anchor_vids and vid != setup.get("start_location")
                  and "hotel" not in venues[vid].get("tags", [])]
    interests = {i for t in travelers for i in t.get("interests", [])}
    candidates.sort(key=lambda vid: (vid not in must, not (set(venues[vid].get("tags", [])) & interests),
                                     venues[vid].get("cost", 0)))

    def dfs(loc, t, ai, items, used):
        if ai == len(anchors) and goal(items):
            return items
        nfree = len(items) - ai
        nxt = anchors[ai] if ai < len(anchors) else None

        # Transition to anchor only if daytime activities have been scheduled
        if nxt and (nfree >= min_act or not candidates or all(c in used for c in candidates)):
            a_s, a_e = to_min(nxt["start"]), to_min(nxt["end"])
            tr = travel_minutes(loc, nxt["venue_id"], venues)
            new_items = [dict(x) for x in items]
            arrival = None
            if new_items and not new_items[-1].get("anchor"):
                last = new_items[-1]
                close = to_min(venues[last["venue_id"]].get("close", "21:30"))
                end = max(to_min(last["end"]), min(close, a_s - tr))
                last["end"] = to_hhmm(end)
                arrival = end + tr
            elif t + tr <= a_s:
                arrival = a_s if not new_items else t + tr
            if arrival is not None and arrival <= a_s and (
                    gap is None or n_groups == 1 or a_s - arrival <= gap or not new_items):
                new_items.append({"venue_id": nxt["venue_id"], "start": nxt["start"], "end": nxt["end"],
                                  "members": list(group), "anchor": True})
                r = dfs(nxt["venue_id"], a_e, ai + 1, new_items, used)
                if r:
                    return r

        if nfree >= MAX_FREE:
            return None
        limit = to_min(nxt["start"]) if nxt else day_e
        for vid in candidates:
            if vid in used:
                continue
            v = venues[vid]
            s = max(t + travel_minutes(loc, vid, venues), to_min(v.get("open", "09:00")))
            e = s + max(45, v.get("min_minutes", 60))
            back = travel_minutes(vid, nxt["venue_id"], venues) if nxt else 0
            if e + back > limit or not ok_venue(vid, s, e):
                continue
            r = dfs(vid, e, ai, items + [{"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e),
                                          "members": list(group)}], used | {vid})
            if r:
                return r
        return None

    start_loc = setup.get("start_location")
    if not start_loc or start_loc not in venues:
        hotels = [vid for vid, v in venues.items() if "hotel" in v.get("tags", [])]
        start_loc = hotels[0] if hotels else next(iter(venues.keys()))
    return dfs(start_loc, to_min(setup.get("day_start", "09:30")), 0, [], set())


def deduplicate_itinerary(itinerary: list[dict]) -> list[dict]:
    """Merge items having identical (venue_id, start, end), combining member lists into a single shared stop."""
    merged: dict[tuple[str, str, str], dict] = {}
    order: list[tuple[str, str, str]] = []
    for it in itinerary:
        key = (it["venue_id"], it["start"], it["end"])
        if key not in merged:
            merged[key] = dict(it)
            merged[key]["members"] = list(it.get("members", []))
            order.append(key)
        else:
            m = set(merged[key]["members"])
            m.update(it.get("members", []))
            merged[key]["members"] = sorted(list(m))
    return [merged[k] for k in order]


def solve(setup: dict):
    """Return a valid multi-day or single-day plan with transit times, or None."""
    venues = venues_for(setup)
    if not venues or len(venues) < 3:
        return None

    setup = sanitize_setup(setup, venues)
    total_days = max(1, min(5, int(setup.get("days", 2))))
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

        # Day anchors: on Day 1, use setup anchors. On Day 2+, select a fresh dining spot for evening convergence
        if day == 1:
            day_anchors = list(setup.get("anchors", []))
        else:
            dinner_candidates = [
                vid for vid, v in avail_venues.items()
                if any(t in v.get("tags", []) for t in ["dining", "food", "restaurant"])
                and vid != setup.get("start_location")
            ]
            if not dinner_candidates:
                dinner_candidates = [vid for vid in avail_venues if vid != setup.get("start_location")]
            if dinner_candidates:
                day_anchors = [{
                    "venue_id": dinner_candidates[0],
                    "start": "18:30",
                    "end": "20:00",
                    "members": [t["name"] for t in setup["travelers"]],
                    "anchor": True
                }]
            else:
                day_anchors = []
        day_setup["anchors"] = day_anchors

        day_items = None
        for grouping in _groupings(day_setup["travelers"]):
            parts = []
            for g in grouping:
                r = _solve_group_with_venues(g, day_setup, len(grouping), avail_venues)
                if r is None:
                    break
                parts.extend(r)
            else:
                raw_it = [{k: v for k, v in it.items() if k != "anchor"} for it in parts]
                day_items = deduplicate_itinerary(raw_it)
                break

        # Fallback relaxation if strict grouping had no solution
        if not day_items:
            relaxed_setup = dict(day_setup)
            relaxed_setup["requirements"] = {**relaxed_setup.get("requirements", {}), "min_activities": 1}
            for grouping in _groupings(relaxed_setup["travelers"]):
                parts = []
                for g in grouping:
                    r = _solve_group_with_venues(g, relaxed_setup, len(grouping), venues)
                    if r is None:
                        break
                    parts.extend(r)
                else:
                    raw_it = [{k: v for k, v in it.items() if k != "anchor"} for it in parts]
                    day_items = deduplicate_itinerary(raw_it)
                    break

        if day_items:
            for it in day_items:
                it["day"] = day
                if "hotel" not in it["venue_id"]:
                    used_across_days.add(it["venue_id"])
            all_day_itineraries.extend(day_items)

    if not all_day_itineraries:
        return None

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
            mode = "walk" if tr_mins <= 15 else "drive"
            prev_name = venues.get(prev_vid, {}).get("name", "Hotel Departure") if prev_vid != hotel_id else hotel_name

            it["transit_from_prev"] = {
                "mode": mode,
                "duration_mins": tr_mins,
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
        "itinerary": all_day_itineraries
    }
