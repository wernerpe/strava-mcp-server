#!/usr/bin/env python3
"""
Update local run data from Strava.

This script fetches running activities from the last few weeks and stores them
locally in the run_data directory. It only adds new runs and preserves existing data.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

from dotenv import load_dotenv

from src.strava_mcp_server.server import StravaClient

# Load .env file explicitly and override any existing environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env_pete"), override=True)

# Configuration
RUN_DATA_DIR = Path("run_data")
LOOKBACK_WEEKS = 4  # How many weeks back to fetch


def ensure_run_data_dir() -> None:
    """Create the run_data directory if it doesn't exist."""
    RUN_DATA_DIR.mkdir(exist_ok=True)
    print(f"Run data directory: {RUN_DATA_DIR.absolute()}")


def get_existing_run_ids() -> Set[int]:
    """
    Get the set of activity IDs that are already stored locally.

    Returns:
        Set of activity IDs that exist in run_data directory
    """
    existing_ids = set()

    if not RUN_DATA_DIR.exists():
        return existing_ids

    for file_path in RUN_DATA_DIR.glob("run_*.json"):
        try:
            # Extract ID from filename: run_12345.json -> 12345
            activity_id = int(file_path.stem.split("_")[1])
            existing_ids.add(activity_id)
        except (IndexError, ValueError):
            print(f"Warning: Could not parse activity ID from {file_path.name}")

    return existing_ids


def save_run(run: Dict, activity_id: int) -> None:
    """
    Save a single run to a JSON file.

    Args:
        run: Dictionary containing run data
        activity_id: Strava activity ID
    """
    file_path = RUN_DATA_DIR / f"run_{activity_id}.json"

    with open(file_path, 'w') as f:
        json.dump(run, f, indent=2)

    print(f"  Saved: {file_path.name}")


def fetch_run_details(client: StravaClient, activity_id: int) -> Dict:
    """
    Fetch detailed information for a single run including streams and laps.

    Args:
        client: Initialized StravaClient
        activity_id: Strava activity ID

    Returns:
        Dictionary with run details, streams, and laps
    """
    run_details = {}

    # Fetch streams (heartrate, pace, altitude, cadence)
    try:
        streams = client.get_activity_streams(
            activity_id,
            ['heartrate', 'pace', 'altitude', 'cadence']
        )
        run_details['streams'] = streams
    except Exception as e:
        print(f"    Warning: Could not fetch streams: {e}")
        run_details['streams'] = None

    # Fetch laps
    try:
        laps = client.get_activity_laps(activity_id)
        run_details['laps'] = laps
    except Exception as e:
        print(f"    Warning: Could not fetch laps: {e}")
        run_details['laps'] = []

    return run_details


def main():
    """Main function to update run data from Strava."""
    print("=" * 80)
    print("STRAVA RUN DATA UPDATER")
    print("=" * 80)

    # Ensure run_data directory exists
    ensure_run_data_dir()

    # Load Strava credentials
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        print("Error: Missing Strava credentials in .env file")
        print("Required: STRAVA_REFRESH_TOKEN, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET")
        return 1

    # Initialize Strava client
    print("\nConnecting to Strava API...")
    client = StravaClient(refresh_token, client_id, client_secret)

    # Get existing run IDs
    existing_ids = get_existing_run_ids()
    print(f"\nFound {len(existing_ids)} existing runs in local storage")

    # Calculate date range
    after_date = datetime.now() - timedelta(weeks=LOOKBACK_WEEKS)
    after_timestamp = int(after_date.timestamp())

    print(f"Fetching runs from the last {LOOKBACK_WEEKS} weeks...")
    print(f"Date range: {after_date.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")

    # Fetch activities
    try:
        all_activities = client.get_activities(limit=200, after=after_timestamp)
    except Exception as e:
        print(f"Error fetching activities: {e}")
        client.close()
        return 1

    # Filter for running activities only
    runs = [a for a in all_activities if 'run' in a.get('sport_type', '').lower()]

    print(f"\nFound {len(runs)} total running activities from Strava")

    # Identify new runs
    new_runs = [r for r in runs if r.get('id') not in existing_ids]

    if not new_runs:
        print("\nNo new runs to add. Database is up to date!")
        client.close()
        return 0

    print(f"New runs to add: {len(new_runs)}")
    print("\n" + "-" * 80)
    print("Fetching detailed data for new runs...")
    print("-" * 80)

    # Fetch and save new runs
    for i, run in enumerate(new_runs, 1):
        activity_id = run.get('id')
        name = run.get('name', 'Unnamed')
        date_str = run.get('start_date', '')[:10]
        distance_km = run.get('distance_metres', 0) / 1000

        print(f"\n[{i}/{len(new_runs)}] {name} ({date_str}) - {distance_km:.2f}km")

        if not activity_id:
            print("  Skipping: No activity ID")
            continue

        # Fetch additional details
        details = fetch_run_details(client, activity_id)

        # Combine basic run data with detailed information
        complete_run = {**run, **details}

        # Save to file
        save_run(complete_run, activity_id)

    # Summary
    print("\n" + "=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print(f"Total runs in database: {len(existing_ids) + len(new_runs)}")
    print(f"New runs added: {len(new_runs)}")
    print(f"Storage location: {RUN_DATA_DIR.absolute()}")

    client.close()
    return 0


if __name__ == "__main__":
    exit(main())