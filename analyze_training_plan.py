#!/usr/bin/env python3
"""
Analyze training plan adherence and show upcoming workouts.

This script compares your actual runs against your training plan and shows:
- Overall plan progress
- Completed vs missed workouts
- Upcoming workouts
- Plan adherence statistics
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


RUN_DATA_DIR = Path("run_data")


def load_training_plan(plan_path: str) -> Optional[Dict]:
    """Load training plan from JSON file."""
    try:
        with open(plan_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Training plan not found at {plan_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in training plan: {e}")
        return None


def load_all_runs() -> List[Dict]:
    """Load all run data from the run_data directory."""
    runs = []

    if not RUN_DATA_DIR.exists():
        return runs

    for file_path in RUN_DATA_DIR.glob("run_*.json"):
        try:
            with open(file_path, 'r') as f:
                run = json.load(f)
                runs.append(run)
        except Exception:
            pass

    return runs


def format_pace(pace_str: str) -> str:
    """Format pace string consistently."""
    if not pace_str or pace_str == "N/A":
        return "N/A"
    return pace_str


def format_distance(km: float) -> str:
    """Format distance consistently."""
    return f"{km:.1f}km"


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    # Handle both ISO format and date-only format
    if 'T' in date_str or 'Z' in date_str:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return datetime.strptime(date_str, '%Y-%m-%d')


def find_run_for_planned_workout(planned_run: Dict, actual_runs: List[Dict]) -> Optional[Dict]:
    """Find actual run that matches a planned workout (within 1 day)."""
    if 'date' not in planned_run:
        return None

    planned_date = parse_date(planned_run['date']).date()

    for run in actual_runs:
        run_date = parse_date(run.get('start_date', '')).date()

        # Check if run is within 1 day of planned date
        if abs((run_date - planned_date).days) <= 1:
            # For non-running activities, we can't match them
            if planned_run['type'] in ['gym', 'cross_training', 'rest']:
                continue

            return run

    return None


def calculate_pace_from_run(run: Dict) -> str:
    """Calculate pace from actual run data."""
    distance = run.get('distance_metres', 0)
    time = run.get('moving_time_seconds', 0)

    if distance > 0 and time > 0:
        speed_mps = distance / time
        pace_min_per_km = 1000 / (speed_mps * 60)
        mins = int(pace_min_per_km)
        secs = int((pace_min_per_km % 1) * 60)
        return f"{mins}:{secs:02d}"

    return "N/A"


def print_plan_overview(plan: Dict):
    """Print overview of the training plan."""
    print("=" * 100)
    print("TRAINING PLAN OVERVIEW")
    print("=" * 100)
    print()

    goal_race = plan.get('goal_race', {})
    print(f"Plan Name:       {plan.get('plan_name', 'Unnamed Plan')}")
    print(f"Goal Race:       {goal_race.get('race_name', 'N/A')} - {goal_race.get('race_type', 'N/A')}")
    print(f"Race Date:       {goal_race.get('date', 'N/A')}")
    print(f"Goal Time:       {goal_race.get('goal_time', 'N/A')}")
    print(f"Goal Pace:       {goal_race.get('goal_pace_min_per_km', 'N/A')} /km")
    print(f"Plan Duration:   {plan.get('plan_start_date', 'N/A')} to {plan.get('plan_end_date', 'N/A')}")
    print()

    # Calculate days until race
    race_date = parse_date(goal_race.get('date', ''))
    today = datetime.now()
    days_until_race = (race_date - today).days

    if days_until_race > 0:
        weeks_until_race = days_until_race / 7
        print(f"Days until race: {days_until_race} ({weeks_until_race:.1f} weeks)")
    elif days_until_race == 0:
        print("Race day is TODAY!")
    else:
        print(f"Race was {abs(days_until_race)} days ago")

    print()


def print_upcoming_workouts(plan: Dict, days_ahead: int = 7):
    """Print upcoming workouts for the next N days."""
    print("=" * 100)
    print(f"UPCOMING WORKOUTS (Next {days_ahead} days)")
    print("=" * 100)
    print()

    today = datetime.now().date()
    upcoming = []

    for week in plan.get('weeks', []):
        for run in week.get('runs', []):
            if 'date' not in run:
                continue

            run_date = parse_date(run['date']).date()
            days_away = (run_date - today).days

            if 0 <= days_away <= days_ahead:
                upcoming.append((days_away, run_date, run))

    # Sort by date
    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        print("No workouts scheduled in the next week.")
        return

    for days_away, run_date, run in upcoming:
        day_label = "TODAY" if days_away == 0 else "TOMORROW" if days_away == 1 else f"in {days_away} days"

        print(f"{run_date.strftime('%A, %B %d')} ({day_label})")
        print(f"  Type: {run['type'].replace('_', ' ').title()}")

        if run['type'] in ['gym', 'cross_training']:
            duration = run.get('duration_minutes', 'N/A')
            print(f"  Duration: {duration} minutes")
        elif run['type'] == 'rest':
            print(f"  Activity: Rest day")
        else:
            distance = run.get('distance_km', 'N/A')
            pace = run.get('target_pace_min_per_km', 'N/A')
            print(f"  Distance: {distance}km")
            print(f"  Target Pace: {pace} /km")

            if 'structure' in run:
                print(f"  Structure: {run['structure']}")

        if 'description' in run:
            print(f"  Notes: {run['description']}")

        print()


def analyze_plan_adherence(plan: Dict, actual_runs: List[Dict]):
    """Analyze how well actual training matches the plan."""
    print("=" * 100)
    print("PLAN ADHERENCE ANALYSIS")
    print("=" * 100)
    print()

    today = datetime.now().date()
    completed_workouts = []
    missed_workouts = []
    upcoming_workouts = []

    for week in plan.get('weeks', []):
        week_num = week.get('week_number')

        for planned_run in week.get('runs', []):
            if 'date' not in planned_run:
                continue

            run_date = parse_date(planned_run['date']).date()

            # Skip future workouts
            if run_date > today:
                upcoming_workouts.append(planned_run)
                continue

            # Try to find matching actual run
            actual_run = find_run_for_planned_workout(planned_run, actual_runs)

            if actual_run:
                completed_workouts.append({
                    'planned': planned_run,
                    'actual': actual_run,
                    'week': week_num
                })
            else:
                # Only count as missed if it's a running workout
                if planned_run['type'] not in ['gym', 'cross_training', 'rest']:
                    missed_workouts.append({
                        'planned': planned_run,
                        'week': week_num
                    })

    # Calculate statistics
    total_planned = len(completed_workouts) + len(missed_workouts)
    completion_rate = (len(completed_workouts) / total_planned * 100) if total_planned > 0 else 0

    print(f"Workouts Completed: {len(completed_workouts)}/{total_planned} ({completion_rate:.1f}%)")
    print(f"Workouts Missed:    {len(missed_workouts)}")
    print()

    # Show missed workouts
    if missed_workouts:
        print("-" * 100)
        print("MISSED WORKOUTS")
        print("-" * 100)
        print()

        for item in missed_workouts[-10:]:  # Show last 10 missed
            planned = item['planned']
            date_str = planned.get('date', 'N/A')
            print(f"{date_str} - Week {item['week']}")
            print(f"  Type: {planned['type'].replace('_', ' ').title()}")

            if 'distance_km' in planned:
                print(f"  Planned: {planned['distance_km']}km @ {planned.get('target_pace_min_per_km', 'N/A')} /km")

            if 'description' in planned:
                print(f"  Description: {planned['description']}")

            print()

    # Show recent completed workouts with comparison
    if completed_workouts:
        print("-" * 100)
        print("RECENT COMPLETED WORKOUTS (Last 5)")
        print("-" * 100)
        print()

        for item in completed_workouts[-5:]:
            planned = item['planned']
            actual = item['actual']
            date_str = planned.get('date', 'N/A')

            print(f"{date_str} - Week {item['week']}: {actual.get('name', 'Unnamed Run')}")

            planned_dist = planned.get('distance_km', 0)
            actual_dist = actual.get('distance_metres', 0) / 1000
            planned_pace = planned.get('target_pace_min_per_km', 'N/A')
            actual_pace = calculate_pace_from_run(actual)

            print(f"  Distance: {actual_dist:.1f}km (planned: {planned_dist}km)")
            print(f"  Pace:     {actual_pace} /km (target: {planned_pace} /km)")

            if 'structure' in planned:
                print(f"  Workout:  {planned['structure']}")

            print()


def main():
    """Main function to analyze training plan."""
    import sys

    # Get plan path from command line or use default
    if len(sys.argv) > 1:
        plan_path = sys.argv[1]
    else:
        plan_path = "training_plan.json"

    # Load training plan
    plan = load_training_plan(plan_path)
    if not plan:
        print("Please provide a valid training plan JSON file.")
        print(f"Usage: python {sys.argv[0]} [path_to_plan.json]")
        return 1

    # Load actual runs
    actual_runs = load_all_runs()

    # Print analyses
    print_plan_overview(plan)
    print_upcoming_workouts(plan, days_ahead=7)
    analyze_plan_adherence(plan, actual_runs)

    print("=" * 100)
    print("END OF ANALYSIS")
    print("=" * 100)

    return 0


if __name__ == "__main__":
    exit(main())