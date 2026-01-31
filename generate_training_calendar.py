#!/usr/bin/env python3
"""
Generate an interactive HTML calendar for training plan visualization.

This script creates a beautiful calendar view showing:
- Planned workouts from your training plan
- Actual runs from your Strava data
- Comparison between planned and actual
- Hover tooltips with detailed information
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import webbrowser


RUN_DATA_DIR = Path("run_data")


def load_training_plan(plan_path: str) -> Optional[Dict]:
    """Load training plan from JSON file."""
    try:
        with open(plan_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading training plan: {e}")
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


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime."""
    if 'T' in date_str or 'Z' in date_str:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return datetime.strptime(date_str, '%Y-%m-%d')


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


def find_run_for_date(date_obj, actual_runs: List[Dict]) -> Optional[Dict]:
    """Find actual run that matches a specific date (within 1 day)."""
    for run in actual_runs:
        run_date = parse_date(run.get('start_date', '')).date()
        if abs((run_date - date_obj).days) <= 1:
            return run
    return None


def generate_html(plan: Dict, actual_runs: List[Dict], output_file: str):
    """Generate the HTML calendar file."""

    # Prepare data structure for calendar
    plan_data = {}
    for week in plan.get('weeks', []):
        for workout in week.get('runs', []):
            if 'date' in workout:
                date_str = workout['date']
                plan_data[date_str] = workout

    # Match actual runs to planned workouts
    actual_data = {}
    for date_str, planned in plan_data.items():
        date_obj = parse_date(date_str).date()
        actual_run = find_run_for_date(date_obj, actual_runs)
        if actual_run:
            actual_data[date_str] = actual_run

    # Determine calendar date range
    plan_start = parse_date(plan.get('plan_start_date', '')).date()
    plan_end = parse_date(plan.get('plan_end_date', '')).date()

    # Start from the first day of the start month
    cal_start = plan_start.replace(day=1)
    # End at the last day of the end month
    cal_end = (plan_end.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    goal_race = plan.get('goal_race', {})

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{plan.get('plan_name', 'Training Calendar')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 3px solid #667eea;
        }}

        .header h1 {{
            font-size: 2.5em;
            color: #2d3748;
            margin-bottom: 15px;
        }}

        .goal-info {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        .goal-item {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.1em;
        }}

        .goal-item strong {{
            display: block;
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}

        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .legend-box {{
            width: 30px;
            height: 30px;
            border-radius: 6px;
            border: 2px solid #e2e8f0;
        }}

        .legend-box.easy {{ background: #48bb78; }}
        .legend-box.workout {{ background: #ed8936; }}
        .legend-box.long-run {{ background: #9f7aea; }}
        .legend-box.race {{ background: #f56565; }}
        .legend-box.rest {{ background: #cbd5e0; }}
        .legend-box.gym {{ background: #4299e1; }}
        .legend-box.cross {{ background: #38b2ac; }}
        .legend-box.completed {{ background: #38a169; border: 3px solid #22543d; }}
        .legend-box.missed {{ background: #fc8181; border: 3px dashed #c53030; }}

        .calendar-grid {{
            display: grid;
            gap: 30px;
        }}

        .month {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 15px;
        }}

        .month-header {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 15px;
            text-align: center;
        }}

        .weekday-header {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }}

        .weekday {{
            text-align: center;
            font-weight: 600;
            color: #4a5568;
            padding: 10px;
            font-size: 0.9em;
        }}

        .days-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
        }}

        .day {{
            aspect-ratio: 1;
            background: white;
            border-radius: 10px;
            padding: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid #e2e8f0;
            position: relative;
            min-height: 100px;
        }}

        .day:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }}

        .day.empty {{
            background: transparent;
            border: none;
            cursor: default;
        }}

        .day.empty:hover {{
            transform: none;
            box-shadow: none;
        }}

        .day.today {{
            border: 3px solid #667eea;
            box-shadow: 0 0 15px rgba(102, 126, 234, 0.3);
        }}

        .day.race-day {{
            background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
            color: white;
            border: 3px solid #9b2c2c;
        }}

        .day-number {{
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 5px;
            font-size: 0.95em;
        }}

        .day.race-day .day-number {{
            color: white;
        }}

        .workout-type {{
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            padding: 4px 6px;
            border-radius: 5px;
            margin-bottom: 4px;
            text-align: center;
            color: white;
        }}

        .workout-type.easy {{ background: #48bb78; }}
        .workout-type.workout {{ background: #ed8936; }}
        .workout-type.long_run {{ background: #9f7aea; }}
        .workout-type.long-run {{ background: #9f7aea; }}
        .workout-type.tuneup_race {{ background: #f56565; }}
        .workout-type.tuneup-race {{ background: #f56565; }}
        .workout-type.rest {{ background: #cbd5e0; color: #4a5568; }}
        .workout-type.gym {{ background: #4299e1; }}
        .workout-type.cross_training {{ background: #38b2ac; }}
        .workout-type.cross-training {{ background: #38b2ac; }}

        .workout-details {{
            font-size: 0.7em;
            color: #4a5568;
            line-height: 1.3;
        }}

        .status-indicator {{
            position: absolute;
            top: 5px;
            right: 5px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}

        .status-indicator.completed {{
            background: #38a169;
            box-shadow: 0 0 8px rgba(56, 161, 105, 0.6);
        }}

        .status-indicator.missed {{
            background: #fc8181;
            box-shadow: 0 0 8px rgba(252, 129, 129, 0.6);
        }}

        .tooltip {{
            position: fixed;
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-size: 0.9em;
            max-width: 350px;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            display: none;
        }}

        .tooltip.show {{
            display: block;
        }}

        .tooltip h4 {{
            margin-bottom: 10px;
            color: #a0aec0;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .tooltip-section {{
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .tooltip-section:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}

        .tooltip-row {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }}

        .tooltip-label {{
            color: #a0aec0;
        }}

        .tooltip-value {{
            font-weight: 600;
        }}

        .comparison {{
            color: #68d391;
        }}

        .comparison.slower {{
            color: #fc8181;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{plan.get('plan_name', 'Training Calendar')}</h1>
            <div class="goal-info">
                <div class="goal-item">
                    <strong>Race</strong>
                    {goal_race.get('race_name', 'N/A')}
                </div>
                <div class="goal-item">
                    <strong>Date</strong>
                    {goal_race.get('date', 'N/A')}
                </div>
                <div class="goal-item">
                    <strong>Goal Time</strong>
                    {goal_race.get('goal_time', 'N/A')}
                </div>
                <div class="goal-item">
                    <strong>Goal Pace</strong>
                    {goal_race.get('goal_pace_min_per_km', 'N/A')} /km
                </div>
            </div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-box easy"></div>
                <span>Easy Run</span>
            </div>
            <div class="legend-item">
                <div class="legend-box workout"></div>
                <span>Workout</span>
            </div>
            <div class="legend-item">
                <div class="legend-box long-run"></div>
                <span>Long Run</span>
            </div>
            <div class="legend-item">
                <div class="legend-box race"></div>
                <span>Race</span>
            </div>
            <div class="legend-item">
                <div class="legend-box gym"></div>
                <span>Gym</span>
            </div>
            <div class="legend-item">
                <div class="legend-box cross"></div>
                <span>Cross Training</span>
            </div>
            <div class="legend-item">
                <div class="legend-box rest"></div>
                <span>Rest</span>
            </div>
            <div class="legend-item">
                <div class="legend-box completed"></div>
                <span>Completed</span>
            </div>
            <div class="legend-item">
                <div class="legend-box missed"></div>
                <span>Missed</span>
            </div>
        </div>

        <div class="calendar-grid" id="calendar">
        </div>
    </div>

    <div class="tooltip" id="tooltip"></div>

    <script>
        const planData = {json.dumps(plan_data)};
        const actualData = {json.dumps(actual_data)};
        const raceDate = '{goal_race.get('date', '')}';

        function generateCalendar() {{
            const calendar = document.getElementById('calendar');
            const startDate = new Date('{cal_start.isoformat()}');
            const endDate = new Date('{cal_end.isoformat()}');
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            let currentDate = new Date(startDate);

            while (currentDate <= endDate) {{
                const monthDiv = document.createElement('div');
                monthDiv.className = 'month';

                const monthHeader = document.createElement('div');
                monthHeader.className = 'month-header';
                monthHeader.textContent = currentDate.toLocaleDateString('en-US', {{ month: 'long', year: 'numeric' }});
                monthDiv.appendChild(monthHeader);

                const weekdayHeader = document.createElement('div');
                weekdayHeader.className = 'weekday-header';
                ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {{
                    const weekday = document.createElement('div');
                    weekday.className = 'weekday';
                    weekday.textContent = day;
                    weekdayHeader.appendChild(weekday);
                }});
                monthDiv.appendChild(weekdayHeader);

                const daysGrid = document.createElement('div');
                daysGrid.className = 'days-grid';

                const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
                const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);

                // Add empty cells for days before month starts
                for (let i = 0; i < firstDay.getDay(); i++) {{
                    const emptyDay = document.createElement('div');
                    emptyDay.className = 'day empty';
                    daysGrid.appendChild(emptyDay);
                }}

                // Add days of the month
                for (let day = 1; day <= lastDay.getDate(); day++) {{
                    const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
                    const dateStr = date.toISOString().split('T')[0];

                    const dayDiv = document.createElement('div');
                    dayDiv.className = 'day';

                    // Check if it's today
                    if (date.getTime() === today.getTime()) {{
                        dayDiv.classList.add('today');
                    }}

                    // Check if it's race day
                    if (dateStr === raceDate) {{
                        dayDiv.classList.add('race-day');
                    }}

                    const dayNumber = document.createElement('div');
                    dayNumber.className = 'day-number';
                    dayNumber.textContent = day;
                    dayDiv.appendChild(dayNumber);

                    const planned = planData[dateStr];
                    const actual = actualData[dateStr];

                    if (planned) {{
                        const workoutType = document.createElement('div');
                        workoutType.className = `workout-type ${{planned.type}}`;
                        workoutType.textContent = planned.type.replace('_', ' ');
                        dayDiv.appendChild(workoutType);

                        if (planned.type !== 'rest' && planned.type !== 'gym' && planned.type !== 'cross_training') {{
                            const details = document.createElement('div');
                            details.className = 'workout-details';
                            if (planned.distance_km) {{
                                details.textContent = `${{planned.distance_km}}km`;
                            }}
                            dayDiv.appendChild(details);
                        }}

                        // Add status indicator
                        if (date < today) {{
                            const statusIndicator = document.createElement('div');
                            statusIndicator.className = 'status-indicator';
                            if (actual) {{
                                statusIndicator.classList.add('completed');
                            }} else if (planned.type !== 'rest' && planned.type !== 'gym' && planned.type !== 'cross_training') {{
                                statusIndicator.classList.add('missed');
                            }}
                            dayDiv.appendChild(statusIndicator);
                        }}

                        dayDiv.addEventListener('mouseenter', (e) => showTooltip(e, dateStr, planned, actual));
                        dayDiv.addEventListener('mouseleave', hideTooltip);
                        dayDiv.addEventListener('mousemove', moveTooltip);
                    }}

                    daysGrid.appendChild(dayDiv);
                }}

                monthDiv.appendChild(daysGrid);
                calendar.appendChild(monthDiv);

                currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
            }}
        }}

        function showTooltip(e, dateStr, planned, actual) {{
            const tooltip = document.getElementById('tooltip');
            let content = `<h4>${{dateStr}}</h4>`;

            content += '<div class="tooltip-section">';
            content += '<strong>PLANNED</strong><br>';
            content += `<div class="tooltip-row"><span class="tooltip-label">Type:</span> <span class="tooltip-value">${{planned.type.replace('_', ' ').toUpperCase()}}</span></div>`;

            if (planned.distance_km) {{
                content += `<div class="tooltip-row"><span class="tooltip-label">Distance:</span> <span class="tooltip-value">${{planned.distance_km}} km</span></div>`;
                content += `<div class="tooltip-row"><span class="tooltip-label">Pace:</span> <span class="tooltip-value">${{planned.target_pace_min_per_km || 'N/A'}} /km</span></div>`;
            }}

            if (planned.duration_minutes) {{
                content += `<div class="tooltip-row"><span class="tooltip-label">Duration:</span> <span class="tooltip-value">${{planned.duration_minutes}} min</span></div>`;
            }}

            if (planned.structure) {{
                content += `<div class="tooltip-row"><span class="tooltip-label">Structure:</span></div>`;
                content += `<div style="margin-top: 5px; font-size: 0.9em;">${{planned.structure}}</div>`;
            }}

            if (planned.description) {{
                content += `<div style="margin-top: 5px; color: #a0aec0; font-size: 0.9em;">${{planned.description}}</div>`;
            }}
            content += '</div>';

            if (actual) {{
                const actualDistance = (actual.distance_metres / 1000).toFixed(2);
                const actualTime = actual.moving_time_seconds;
                const actualPace = calculatePace(actual);

                content += '<div class="tooltip-section">';
                content += '<strong>ACTUAL</strong><br>';
                content += `<div class="tooltip-row"><span class="tooltip-label">Name:</span> <span class="tooltip-value">${{actual.name || 'Unnamed'}}</span></div>`;
                content += `<div class="tooltip-row"><span class="tooltip-label">Distance:</span> <span class="tooltip-value">${{actualDistance}} km</span></div>`;
                content += `<div class="tooltip-row"><span class="tooltip-label">Pace:</span> <span class="tooltip-value">${{actualPace}} /km</span></div>`;
                content += `<div class="tooltip-row"><span class="tooltip-label">Time:</span> <span class="tooltip-value">${{formatTime(actualTime)}}</span></div>`;

                // Add comparison if applicable
                if (planned.target_pace_min_per_km && actualPace !== 'N/A') {{
                    const plannedSeconds = paceToSeconds(planned.target_pace_min_per_km);
                    const actualSeconds = paceToSeconds(actualPace);
                    const diff = actualSeconds - plannedSeconds;
                    const diffStr = Math.abs(diff).toFixed(0);
                    const compClass = diff <= 0 ? 'comparison' : 'comparison slower';
                    const compText = diff <= 0 ? `${{diffStr}}s faster` : `${{diffStr}}s slower`;
                    content += `<div class="tooltip-row"><span class="tooltip-label">vs Target:</span> <span class="${{compClass}}">${{compText}}</span></div>`;
                }}

                content += '</div>';
            }} else {{
                const dateObj = new Date(dateStr);
                const today = new Date();
                today.setHours(0, 0, 0, 0);

                if (dateObj < today && planned.type !== 'rest' && planned.type !== 'gym' && planned.type !== 'cross_training') {{
                    content += '<div class="tooltip-section" style="color: #fc8181;">';
                    content += '<strong>MISSED</strong><br>';
                    content += 'No run recorded for this workout';
                    content += '</div>';
                }}
            }}

            tooltip.innerHTML = content;
            tooltip.classList.add('show');
            moveTooltip(e);
        }}

        function hideTooltip() {{
            const tooltip = document.getElementById('tooltip');
            tooltip.classList.remove('show');
        }}

        function moveTooltip(e) {{
            const tooltip = document.getElementById('tooltip');
            tooltip.style.left = (e.clientX + 20) + 'px';
            tooltip.style.top = (e.clientY + 20) + 'px';
        }}

        function calculatePace(run) {{
            const distance = run.distance_metres;
            const time = run.moving_time_seconds;

            if (distance > 0 && time > 0) {{
                const speedMps = distance / time;
                const paceMinPerKm = 1000 / (speedMps * 60);
                const mins = Math.floor(paceMinPerKm);
                const secs = Math.floor((paceMinPerKm % 1) * 60);
                return `${{mins}}:${{secs.toString().padStart(2, '0')}}`;
            }}
            return 'N/A';
        }}

        function formatTime(seconds) {{
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);

            if (hours > 0) {{
                return `${{hours}}:${{minutes.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
            }}
            return `${{minutes}}:${{secs.toString().padStart(2, '0')}}`;
        }}

        function paceToSeconds(paceStr) {{
            const parts = paceStr.split(':');
            return parseInt(parts[0]) * 60 + parseInt(parts[1]);
        }}

        generateCalendar();
    </script>
</body>
</html>'''

    with open(output_file, 'w') as f:
        f.write(html_content)


def main():
    """Main function to generate training calendar."""
    import sys

    # Get plan path from command line or use default
    if len(sys.argv) > 1:
        plan_path = sys.argv[1]
    else:
        plan_path = "training_plan.json"

    output_file = "training_calendar.html"

    # Load training plan
    print(f"Loading training plan from {plan_path}...")
    plan = load_training_plan(plan_path)
    if not plan:
        print("Please provide a valid training plan JSON file.")
        print(f"Usage: python {sys.argv[0]} [path_to_plan.json]")
        return 1

    # Load actual runs
    print("Loading actual run data...")
    actual_runs = load_all_runs()
    print(f"Loaded {len(actual_runs)} runs")

    # Generate HTML
    print(f"Generating calendar HTML to {output_file}...")
    generate_html(plan, actual_runs, output_file)

    print(f"\nCalendar generated successfully!")
    print(f"Opening {output_file} in your browser...")

    # Open in browser
    webbrowser.open('file://' + os.path.abspath(output_file))

    return 0


if __name__ == "__main__":
    exit(main())