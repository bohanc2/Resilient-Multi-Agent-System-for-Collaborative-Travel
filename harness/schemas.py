"""Pydantic schemas for structured outputs across workers and supervisor."""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ItineraryItem(BaseModel):
    venue_id: str
    start: str
    end: str
    members: List[str]
    day: int = 1

    @field_validator("start", "end")
    @classmethod
    def validate_time(cls, v: str) -> str:
        parts = str(v).strip().split(":")
        if len(parts) != 2:
            raise ValueError(f"Time '{v}' must be in HH:MM format")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 24 and 0 <= m <= 59):
            raise ValueError(f"Time '{v}' out of valid range")
        return f"{h:02d}:{m:02d}"


class PlanOutput(BaseModel):
    feasible: bool = True
    reason: str = ""
    itinerary: List[ItineraryItem] = Field(default_factory=list)
    status: Optional[str] = "OK"
    total_days: int = 1
    days: int = 1
    duration_days: int = 1
    city: Optional[str] = ""
    center: Optional[List[float]] = None
    collected_candidates: Optional[list] = Field(default_factory=list)


class SupervisorDecision(BaseModel):
    next: Literal["group_sync", "contingency", "base_planner", "declare_infeasible", "submit_best"]
    instruction: Optional[str] = ""
    reason: Optional[str] = ""
