#!/usr/bin/env python3
"""
Pull the last 2 weeks of running activities from Strava.
"""

import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Import the StravaClient from the server module
from src.strava_mcp_server.server import StravaClient

load_dotenv()

def main():
    # Initialize Strava client
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("Error: Missing Strava credentials in .env file")
        return

    print("Connecting to Strava API...")
    client = StravaClient(refresh_token, client_id, client_secret)

    # Get activities from the last 14 days
    print("Fetching your running activities from the last 2 weeks...")
    after_date = datetime.now() - timedelta(days=14)
    after_timestamp = int(after_date.timestamp())

    all_activities = client.get_activities(limit=50, after=after_timestamp)

    # Filter for running activities only
    runs = [a for a in all_activities if 'run' in a.get('sport_type', '').lower()]

    print(f"\nFound {len(runs)} running activities from the last 2 weeks\n")

    if not runs:
        print("No running activities found in the last 2 weeks.")
        client.close()
        return

    # Fetch heartrate and pace streams for each run
    print("Fetching heartrate and pace streams for each run...")
    for i, run in enumerate(runs):
        activity_id = run.get('id')
        if activity_id:
            try:
                streams = client.get_activity_streams(activity_id, ['heartrate', 'pace'])
                run['streams'] = streams
                print(f"  [{i+1}/{len(runs)}] Fetched streams for: {run.get('name', 'Unnamed')}")
            except Exception as e:
                print(f"  [{i+1}/{len(runs)}] Warning: Could not fetch streams for {run.get('name', 'Unnamed')}: {e}")
                run['streams'] = None
        else:
            run['streams'] = None
    print()

    # Display detailed info for each run
    print("=" * 100)
    print(f"{'Date':<12} {'Name':<30} {'Distance (km)':<15} {'Time':<12} {'Pace (min/km)'}")
    print("=" * 100)

    for run in runs:
        date_str = run.get('start_date', '')[:10]
        name = run.get('name', 'Unnamed')[:29]
        distance_m = run.get('distance_metres', 0)
        distance_km = distance_m / 1000
        time_sec = run.get('moving_time_seconds', 0)
        time_min = time_sec / 60

        # Calculate pace (min/km)
        pace = (time_sec / 60) / distance_km if distance_km > 0 else 0
        pace_str = f"{int(pace)}:{int((pace % 1) * 60):02d}" if pace > 0 else "N/A"

        # Format time as HH:MM:SS
        hours = int(time_sec // 3600)
        minutes = int((time_sec % 3600) // 60)
        seconds = int(time_sec % 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        print(f"{date_str:<12} {name:<30} {distance_km:<15.2f} {time_str:<12} {pace_str}")

    # Save to JSON file
    output_file = "recent_runs.json"
    with open(output_file, 'w') as f:
        json.dump(runs, f, indent=2)

    print("=" * 100)
    print(f"\nData saved to {output_file}")

    # Calculate summary stats
    total_distance_km = sum(r.get('distance_metres', 0) for r in runs) / 1000
    total_time_sec = sum(r.get('moving_time_seconds', 0) for r in runs)
    total_time_hours = total_time_sec / 3600
    avg_pace_min_per_km = (total_time_sec / 60) / total_distance_km if total_distance_km > 0 else 0

    print("\nSummary (Last 2 Weeks):")
    print(f"  Total runs: {len(runs)}")
    print(f"  Total distance: {total_distance_km:.2f} km")
    print(f"  Total time: {total_time_hours:.2f} hours")
    print(f"  Average pace: {int(avg_pace_min_per_km)}:{int((avg_pace_min_per_km % 1) * 60):02d} min/km")
    print(f"  Average run distance: {total_distance_km / len(runs):.2f} km")

    # Stream data summary
    runs_with_streams = sum(1 for r in runs if r.get('streams'))
    print(f"\nStream Data:")
    print(f"  Runs with heartrate/pace data: {runs_with_streams}/{len(runs)}")

    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()