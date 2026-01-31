#!/usr/bin/env python3
"""
Pull the last 3 weeks of running activities from Strava.
"""

import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Import the StravaClient from the server module
from src.strava_mcp_server.server import StravaClient

load_dotenv()

def format_pace(speed_mps):
    """Convert speed in m/s to pace in min/km format."""
    if speed_mps <= 0:
        return "N/A"
    pace_min_per_km = 1000 / (speed_mps * 60)
    mins = int(pace_min_per_km)
    secs = int((pace_min_per_km % 1) * 60)
    return f"{mins}:{secs:02d}"


def generate_workout_summary(run):
    """
    Generate a summary of a run based on its laps.
    """
    laps = run.get('laps', [])
    if not laps:
        return "No lap data available"

    name = run.get('name', 'Unnamed Run')
    date_str = run.get('start_date', '')[:10]
    total_laps = len(laps)

    summary_lines = [
        f"\nRun: {name}",
        f"Date: {date_str}",
        f"Total laps: {total_laps}",
        "\nLap breakdown:"
    ]

    for i, lap in enumerate(laps, 1):
        distance_m = lap.get('distance', 0)
        distance_km = distance_m / 1000
        time_sec = lap.get('moving_time', 0)
        avg_speed = lap.get('average_speed', 0)
        max_speed = lap.get('max_speed', 0)
        avg_hr = lap.get('average_heartrate', 0)
        max_hr = lap.get('max_heartrate', 0)

        # Format time
        mins = int(time_sec // 60)
        secs = int(time_sec % 60)
        time_str = f"{mins}:{secs:02d}"

        # Calculate pace
        pace_str = format_pace(avg_speed)

        lap_info = f"  Lap {i}: {distance_km:.2f}km in {time_str} @ {pace_str}/km"

        if avg_hr > 0:
            lap_info += f" | HR: {int(avg_hr)} bpm (max: {int(max_hr)})"

        summary_lines.append(lap_info)

    return "\n".join(summary_lines)


def plot_run_streams(runs):
    """Plot heartrate and pace streams for runs that have stream data."""
    runs_with_streams = [r for r in runs if r.get('streams')]

    if not runs_with_streams:
        print("No stream data available to plot.")
        return

    for run in runs_with_streams:
        streams = run['streams']
        name = run.get('name', 'Unnamed Run')
        date_str = run.get('start_date', '')[:10]

        # Check if we have the required stream data
        has_heartrate = 'heartrate' in streams and bool(streams['heartrate'])
        has_pace = 'pace' in streams and bool(streams['pace'])

        if not has_heartrate and not has_pace:
            continue

        # Create figure with subplots
        num_plots = sum([has_heartrate, has_pace])
        fig, axes = plt.subplots(num_plots, 1, figsize=(12, 4 * num_plots))

        if num_plots == 1:
            axes = [axes]

        plot_idx = 0

        # Plot heartrate
        if has_heartrate:
            hr_data = streams['heartrate'].get('data', [])
            if hr_data:
                axes[plot_idx].plot(hr_data, color='#FC4C02', linewidth=2)
                axes[plot_idx].set_ylabel('Heart Rate (bpm)', fontsize=12, fontweight='bold')
                axes[plot_idx].set_xlabel('Time (seconds)', fontsize=10)
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title(f'Heart Rate - {name} ({date_str})', fontsize=14, fontweight='bold')
                plot_idx += 1

        # Plot pace
        if has_pace:
            pace_data = streams['pace'].get('data', [])
            if pace_data:
                # Convert pace from m/s to min/km
                pace_min_km = [1000 / (p * 60) if p > 0 else 0 for p in pace_data]
                axes[plot_idx].plot(pace_min_km, color='#1E88E5', linewidth=2)
                axes[plot_idx].set_ylabel('Pace (min/km)', fontsize=12, fontweight='bold')
                axes[plot_idx].set_xlabel('Time (seconds)', fontsize=10)
                axes[plot_idx].invert_yaxis()  # Lower pace is better (faster)
                axes[plot_idx].grid(True, alpha=0.3)
                axes[plot_idx].set_title(f'Pace - {name} ({date_str})', fontsize=14, fontweight='bold')

        plt.tight_layout()

        # Save the plot
        filename = f"run_{run.get('id')}_{date_str}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"  Saved plot: {filename}")
        plt.close()

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

    # Get activities from the last 21 days
    print("Fetching your running activities from the last 3 weeks...")
    after_date = datetime.now() - timedelta(days=21)
    after_timestamp = int(after_date.timestamp())

    all_activities = client.get_activities(limit=50, after=after_timestamp)

    # Filter for running activities only
    runs = [a for a in all_activities if 'run' in a.get('sport_type', '').lower()]

    print(f"\nFound {len(runs)} running activities from the last 3 weeks\n")

    if not runs:
        print("No running activities found in the last 3 weeks.")
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

    # Fetch laps for each run
    print("Fetching laps for each run...")
    for i, run in enumerate(runs):
        activity_id = run.get('id')
        if activity_id:
            try:
                laps = client.get_activity_laps(activity_id)
                run['laps'] = laps
                print(f"  [{i+1}/{len(runs)}] Fetched {len(laps)} laps for: {run.get('name', 'Unnamed')}")
            except Exception as e:
                print(f"  [{i+1}/{len(runs)}] Warning: Could not fetch laps for {run.get('name', 'Unnamed')}: {e}")
                run['laps'] = []
        else:
            run['laps'] = []
    print()

    # Plot the stream data
    print("Creating plots for runs with stream data...")
    plot_run_streams(runs)
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

    print("\nSummary (Last 3 Weeks):")
    print(f"  Total runs: {len(runs)}")
    print(f"  Total distance: {total_distance_km:.2f} km")
    print(f"  Total time: {total_time_hours:.2f} hours")
    print(f"  Average pace: {int(avg_pace_min_per_km)}:{int((avg_pace_min_per_km % 1) * 60):02d} min/km")
    print(f"  Average run distance: {total_distance_km / len(runs):.2f} km")

    # Stream data summary
    runs_with_streams = sum(1 for r in runs if r.get('streams'))
    print(f"\nStream Data:")
    print(f"  Runs with heartrate/pace data: {runs_with_streams}/{len(runs)}")

    # Display lap summaries for all runs
    runs_with_laps = [r for r in runs if r.get('laps')]
    if runs_with_laps:
        print("\n" + "=" * 100)
        print("LAP SUMMARIES")
        print("=" * 100)
        for run in runs_with_laps:
            summary = generate_workout_summary(run)
            print(summary)
        print("=" * 100)

    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()