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
    day_s = to_min(setup.get("day_start", "09:30"))
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

        # Time suitability guard
        suit = v.get("time_suitability", "any")
        if suit == "daytime" and s >= to_min("18:00"):
            return False
        if suit == "evening" and e <= to_min("17:00"):
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

    must = set(req.get("must_visit", [])) | {p["venue_id"] for p in req.get("preserve_venues", [])
                                             if (p.get("members", "all") == "all" or set(p.get("members", [])) & set(group)) and p.get("venue_id") in venues}

    candidates = [vid for vid in venues if vid not in anchor_vids and vid != setup.get("start_location")
                  and "hotel" not in venues[vid].get("tags", [])]
    interests = {i for t in travelers for i in t.get("interests", [])}

    def candidate_score(vid, curr_t, has_lunch, nxt_anchor_vid=None):
        v = venues[vid]
        v_tags = set(v.get("tags", []))
        score = 0
        if vid in must:
            score += 50
        if v_tags & interests:
            score += 15
        if 11 * 60 + 30 <= curr_t <= 13 * 60 + 30 and not has_lunch and (v_tags & {"food", "lunch", "dining", "restaurant", "cafe"}):
            score += 30
        if curr_t >= 19 * 60 + 30 and v.get("time_suitability") == "evening":
            score += 20
        if curr_t >= 15 * 60 + 30 and nxt_anchor_vid:
            tr_to_anchor = travel_minutes(vid, nxt_anchor_vid, venues)
            if tr_to_anchor <= 20:
                score += 15
        return -score

    def dfs(loc, t, ai, items, used):
        if ai == len(anchors):
            if goal(items):
                # Check evening activity after dinner before day_e
                if t < day_e - 45:
                    evening_cands = [vid for vid in candidates if vid not in used and venues[vid].get("time_suitability") in ("evening", "any")]
                    evening_cands.sort(key=lambda vid: candidate_score(vid, t, True))
                    for evid in evening_cands[:3]:
                        ev = venues[evid]
                        es = max(t + travel_minutes(loc, evid, venues), to_min(ev.get("open", "09:00")))
                        dur = max(45, min(90, ev.get("duration_mins", 60)))
                        ee = es + dur
                        if ee <= day_e and ok_venue(evid, es, ee):
                            new_items = items + [{"venue_id": evid, "start": to_hhmm(es), "end": to_hhmm(ee), "members": list(group)}]
                            if goal(new_items):
                                return new_items
                return items
            elif len(anchors) > 0:
                return None

        nxt = anchors[ai] if ai < len(anchors) else None
        if nxt:
            a_s, a_e = to_min(nxt["start"]), to_min(nxt["end"])
            tr = travel_minutes(loc, nxt["venue_id"], venues)
            nfree = len(items) - ai

            # Transition to anchor once daytime schedule reaches late afternoon or candidates exhausted
            can_fit_more = (t < 16 * 60 + 45) and any(
                t + travel_minutes(loc, vid, venues) + 45 + travel_minutes(vid, nxt["venue_id"], venues) <= a_s
                for vid in candidates if vid not in used
            )

            if not can_fit_more:
                new_items = [dict(x) for x in items]
                arrival = None
                if new_items and not new_items[-1].get("anchor"):
                    last = new_items[-1]
                    last_v = venues[last["venue_id"]]
                    last_s = to_min(last["start"])
                    close = to_min(last_v.get("close", "21:30"))
                    # Cap venue visit duration: strictly never exceed 2.5 hours (150 mins)
                    max_dur = min(150, last_v.get("max_duration_mins", 150))
                    min_dur = last_v.get("min_minutes", 60)
                    end = min(close, a_s - tr)
                    if end - last_s > max_dur:
                        end = last_s + max_dur
                    if end - last_s >= min_dur:
                        last["end"] = to_hhmm(end)
                        arrival = end + tr
                    else:
                        arrival = None
                elif t + tr <= a_s:
                    arrival = a_s if not new_items else t + tr

                if arrival is not None and arrival <= a_s and (a_s - arrival <= 35 or not new_items):
                    new_items.append({"venue_id": nxt["venue_id"], "start": nxt["start"], "end": nxt["end"],
                                      "members": list(group), "anchor": True, "is_shared": True})
                    r = dfs(nxt["venue_id"], a_e, ai + 1, new_items, used)
                    if r:
                        return r

        nfree = len(items) - ai
        if nfree >= 5:
            return None

        limit_s = a_s if nxt else day_e
        has_lunch = any(
            any(tag in venues[it["venue_id"]].get("tags", []) for tag in ["food", "lunch", "dining", "restaurant"])
            for it in items
        )
        avail = [vid for vid in candidates if vid not in used]
        avail.sort(key=lambda vid: candidate_score(vid, t, has_lunch, nxt["venue_id"] if nxt else None))

        for vid in avail[:4]:
            v = venues[vid]
            s = max(t + travel_minutes(loc, vid, venues), to_min(v.get("open", "09:00")))
            dur = max(v.get("min_minutes", 60), min(120, v.get("duration_mins", v.get("min_minutes", 60))))
            e = s + dur
            back = travel_minutes(vid, nxt["venue_id"], venues) if nxt else 0
            if e + back > limit_s or not ok_venue(vid, s, e):
                continue
                continue
            r = dfs(vid, e, ai, items + [{"venue_id": vid, "start": to_hhmm(s), "end": to_hhmm(e), "members": list(group)}], used | {vid})
            if r:
                return r
        return None

    start_loc = setup.get("start_location")
    if not start_loc or start_loc not in venues:
        hotels = [vid for vid, v in venues.items() if "hotel" in v.get("tags", [])]
        start_loc = hotels[0] if hotels else next(iter(venues.keys()))
    return dfs(start_loc, day_s, 0, [], set())


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
            for g in grouping:
                r = _solve_group_with_venues(g, day_setup, len(grouping), avail_venues)
                if r is None:
                    break
                parts.extend(r)
            else:
                raw_it = [{k: v for k, v in it.items() if k != "anchor"} for it in parts]
                day_items = deduplicate_itinerary(raw_it, total_travelers)
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
                    day_items = deduplicate_itinerary(raw_it, total_travelers)
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
