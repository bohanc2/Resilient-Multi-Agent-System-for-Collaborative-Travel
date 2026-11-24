"""Brute-force reference solver. Used only offline by make_tasks.py to prove that every
"answerable" task has at least one valid plan (and to store it as the reference answer)."""
from __future__ import annotations

from .checker import check_plan
from .data import rainy_hours, to_hhmm, to_min, travel_minutes, venues_for

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
    """Ensure start_location and anchors belong to the current city's venues."""
    setup = dict(setup)
    city = setup.get("city", "taipei").lower()

    # 1. Sanitize start_location
    start_loc = setup.get("start_location")
    if not start_loc or start_loc not in venues:
        from .cities import CITY_INFO
        if city in CITY_INFO and CITY_INFO[city]["hotel"] in venues:
            setup["start_location"] = CITY_INFO[city]["hotel"]
        else:
            hotels = [vid for vid, v in venues.items() if "hotel" in v.get("tags", []) or "lodging" in v.get("tags", [])]
            setup["start_location"] = hotels[0] if hotels else next(iter(venues.keys()), "hotel_ximen")

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
                else:
                    replacement_vid = next(iter(venues.keys()))
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


def _solve_group(group, setup, n_groups):
    venues = venues_for(setup)
    setup = sanitize_setup(setup, venues)
    req = setup.get("requirements", {})
    travelers = [t for t in setup["travelers"] if t["name"] in group]
    max_walk = min(t.get("max_walk", 3) for t in travelers)
    rain = rainy_hours(setup)
    wd = setup.get("weekday", "Sat")
    anchors = sorted([a for a in setup.get("anchors", [])
                      if a.get("members", "all") == "all" or set(a["members"]) & set(group)],
                     key=lambda a: to_min(a["start"]))
    anchor_vids = {a["venue_id"] for a in anchors}
    gap = req.get("max_regroup_gap_min")
    must = set(req.get("must_visit", [])) | {p["venue_id"] for p in req.get("preserve_venues", [])
                                            if p.get("members", "all") == "all" or set(p["members"]) & set(group)}
    day_e = to_min(setup.get("day_end", "22:00"))
    min_act = req.get("min_activities", 0)

    def ok_venue(vid, s, e):
        v = venues[vid]
        if wd in v["closed_days"] or v["walk"] > max_walk:
            return False
        if s < to_min(v["open"]) or e > to_min(v["close"]):
            return False
        if not v["indoor"] and any(s < (h + 1) * 60 and e > h * 60 for h in rain):
            return False
        return True

    def goal(items):
        free = [it for it in items if not it.get("anchor")]
        if len(free) < min_act:
            return False
        vids = {it["venue_id"] for it in items}
        if not must <= vids:
            return False
        for t in travelers:
            if req.get("interest_coverage") and t.get("interests"):
                if not any(set(venues[it["venue_id"]]["tags"]) & set(t["interests"]) for it in free):
                    return False
            if sum(venues[it["venue_id"]]["cost"] for it in items) > t.get("budget", 10 ** 9):
                return False
        return True

    candidates = [vid for vid in venues if vid not in anchor_vids and vid != setup.get("start_location")
                  and "hotel" not in venues[vid]["tags"]]
    interests = {i for t in travelers for i in t.get("interests", [])}
    candidates.sort(key=lambda vid: (vid not in must, not (set(venues[vid]["tags"]) & interests),
                                     venues[vid]["cost"]))

    def dfs(loc, t, ai, items, used):
        if ai == len(anchors) and goal(items):
            return items
        nfree = len(items) - ai
        nxt = anchors[ai] if ai < len(anchors) else None
        if nxt:  # go to next anchor
            a_s, a_e = to_min(nxt["start"]), to_min(nxt["end"])
            tr = travel_minutes(loc, nxt["venue_id"], venues)
            new_items = [dict(x) for x in items]
            arrival = None
            if new_items and not new_items[-1].get("anchor"):
                last = new_items[-1]
                close = to_min(venues[last["venue_id"]]["close"])
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
            s = max(t + travel_minutes(loc, vid, venues), to_min(v["open"]))
            e = s + v["min_minutes"]
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
        start_loc = next(iter(venues.keys()), "hotel_ximen")
    return dfs(start_loc, to_min(setup.get("day_start", "09:00")), 0, [], set())


def solve(setup: dict):
    """Return a valid plan or None."""
    venues = venues_for(setup)
    setup = sanitize_setup(setup, venues)
    for grouping in _groupings(setup["travelers"]):
        parts = []
        for g in grouping:
            r = _solve_group(g, setup, len(grouping))
            if r is None:
                break
            parts.extend(r)
        else:
            plan = {"feasible": True, "reason": "reference solution",
                    "itinerary": [{k: v for k, v in it.items() if k != "anchor"} for it in parts]}
            if not check_plan(plan, setup):
                return plan
    return None
