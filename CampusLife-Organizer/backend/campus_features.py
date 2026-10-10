from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _time_minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def forecast_campus_demand(payload: dict[str, Any]) -> dict[str, Any]:
    end_minute = _time_minutes(payload["class_end_time"])
    expected_visitors = payload["students_finishing"] * payload["visit_probability"]
    horizon = payload["forecast_minutes"]
    mean_walk = payload["average_walk_minutes"]
    spread = payload["walk_time_spread_minutes"]
    counters = payload["counters"]
    capacity_per_minute = sum(counter["service_rate_per_minute"] for counter in counters)

    weights: list[float] = []
    for minute in range(horizon):
        if spread == 0:
            weight = 1.0 if minute == mean_walk else 0.0
        else:
            weight = max(0.0, 1 - abs(minute - mean_walk) / (spread + 1))
        weights.append(weight)
    weight_sum = sum(weights)
    if weight_sum == 0:
        weights[min(mean_walk, horizon - 1)] = 1.0
        weight_sum = 1.0

    arrivals = [expected_visitors * weight / weight_sum for weight in weights]
    queues = [0.0 for _ in counters]
    windows = []
    for offset in range(0, horizon, 5):
        bucket_arrivals = sum(arrivals[offset:offset + 5])
        for queue_index, counter in enumerate(counters):
            queues[queue_index] = max(
                0.0,
                queues[queue_index] - counter["service_rate_per_minute"] * 5,
            )
        remaining = bucket_arrivals
        bucket_waits: list[float] = []
        while remaining > 0.001:
            counter_index = min(
                range(len(counters)),
                key=lambda index: queues[index] / counters[index]["service_rate_per_minute"],
            )
            counter = counters[counter_index]
            predicted_wait = queues[counter_index] / counter["service_rate_per_minute"]
            chunk = min(remaining, max(1.0, counter["service_rate_per_minute"] * 5))
            queues[counter_index] += chunk
            bucket_waits.append(predicted_wait)
            remaining -= chunk

        avg_wait = (
            sum(bucket_waits) / len(bucket_waits)
            if bucket_waits
            else min(queues[index] / counters[index]["service_rate_per_minute"] for index in range(len(counters)))
        )
        windows.append({
            "from": (end_minute + offset) % (24 * 60),
            "to": (end_minute + min(offset + 5, horizon)) % (24 * 60),
            "expected_arrivals": round(bucket_arrivals, 1),
            "estimated_wait_minutes": round(avg_wait, 1),
        })

    sorted_windows = sorted(windows, key=lambda window: window["estimated_wait_minutes"])
    peak = max(windows, key=lambda window: window["expected_arrivals"])
    recommendations = [
        {
            "arrival_time": f"{window['from'] // 60:02d}:{window['from'] % 60:02d}",
            "estimated_wait_minutes": window["estimated_wait_minutes"],
            "reason": "Lower predicted queue than the busiest arrival window.",
        }
        for window in sorted_windows[:2]
    ]

    return {
        "expected_visitors": round(expected_visitors, 1),
        "capacity_per_minute": round(capacity_per_minute, 2),
        "peak_window": {
            "from": f"{peak['from'] // 60:02d}:{peak['from'] % 60:02d}",
            "to": f"{peak['to'] // 60:02d}:{peak['to'] % 60:02d}",
            "expected_arrivals": peak["expected_arrivals"],
        },
        "arrival_curve": [
            {
                "time": f"{((end_minute + window['from']) % (24 * 60)) // 60:02d}:{((end_minute + window['from']) % (24 * 60)) % 60:02d}",
                "expected_arrivals": window["expected_arrivals"],
                "estimated_wait_minutes": window["estimated_wait_minutes"],
            }
            for window in windows
        ],
        "recommendations": recommendations,
        "confidence": "low",
        "data_label": "Illustrative forecast from user-provided assumptions; not live crowd data.",
        "assumptions": {
            "students_finishing": payload["students_finishing"],
            "visit_probability": payload["visit_probability"],
            "average_walk_minutes": mean_walk,
            "walk_time_spread_minutes": spread,
        },
    }


def build_event_agenda(payload: dict[str, Any]) -> list[dict[str, Any]]:
    start = payload["starts_at"]
    end = payload["ends_at"]
    if end <= start:
        raise ValueError("Event end must be after event start")
    duration = end - start
    setup = timedelta(minutes=payload["setup_minutes"])
    break_duration = timedelta(minutes=payload["break_minutes"])
    judging = timedelta(minutes=payload["judging_minutes"])
    submission_offset = timedelta(minutes=payload["submission_minutes_before_end"])
    judging_start = max(start, end - judging)
    submission_deadline = max(start, min(end - submission_offset, judging_start))
    agenda = [
        {
            "title": "Setup and check-in",
            "starts_at": (start - setup).isoformat(),
            "ends_at": start.isoformat(),
        },
        {
            "title": "Event kickoff",
            "starts_at": start.isoformat(),
            "ends_at": (start + min(timedelta(minutes=30), duration / 6)).isoformat(),
        },
    ]
    work_start = start + min(timedelta(minutes=30), duration / 6)
    work_end = submission_deadline
    if work_end > work_start:
        midpoint = work_start + (work_end - work_start) / 2
        break_end = min(midpoint + break_duration, work_end)
        agenda.extend([
            {
                "title": "Build sprint",
                "starts_at": work_start.isoformat(),
                "ends_at": midpoint.isoformat(),
            },
            {
                "title": "Break",
                "starts_at": midpoint.isoformat(),
                "ends_at": break_end.isoformat(),
            },
            {
                "title": "Final build",
                "starts_at": break_end.isoformat(),
                "ends_at": work_end.isoformat(),
            },
        ])
    agenda.append({
        "title": "Submission deadline",
        "starts_at": submission_deadline.isoformat(),
        "ends_at": submission_deadline.isoformat(),
    })
    if judging_start < end:
        agenda.append({
            "title": "Judging",
            "starts_at": max(start, judging_start).isoformat(),
            "ends_at": end.isoformat(),
        })
    return agenda


def match_student_profiles(target: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_skills = {skill.strip().lower() for skill in target.get("skills", [])}
    target_interests = {value.strip().lower() for value in target.get("interests", [])}
    matches = []
    for candidate in candidates:
        skills = {skill.strip().lower() for skill in candidate.get("skills", [])}
        interests = {value.strip().lower() for value in candidate.get("interests", [])}
        complementary = skills - target_skills
        shared_interests = interests & target_interests
        goal_match = bool(
            target.get("project_goal")
            and candidate.get("project_goal")
            and target["project_goal"].strip().lower() == candidate["project_goal"].strip().lower()
        )
        score = min(100, len(complementary) * 22 + len(shared_interests) * 12 + (20 if goal_match else 0))
        reasons = []
        if complementary:
            reasons.append(f"Complementary skills: {', '.join(sorted(complementary))}")
        if shared_interests:
            reasons.append(f"Shared interests: {', '.join(sorted(shared_interests))}")
        if goal_match:
            reasons.append("Aligned project goal")
        common_interest = sorted(shared_interests)[0] if shared_interests else "campus projects"
        matches.append({
            "user_id": candidate["user_id"],
            "name": candidate["name"],
            "skills": sorted(skills),
            "availability": candidate["availability"],
            "score": score,
            "reasons": reasons or ["Profile has limited overlap; consider a low-pressure introduction."],
            "starter": f"Hi {candidate['name'].split()[0]}, I noticed we both like {common_interest}. Would you be open to chatting about a project?",
        })
    return sorted(matches, key=lambda item: item["score"], reverse=True)
