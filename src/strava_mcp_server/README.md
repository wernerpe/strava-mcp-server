# Strava MCP Server - Tool Reference

This document describes all MCP tools available in the Strava MCP Server.

## Activity Tools

These tools query your Strava data directly.

### `get_activities`
Get the authenticated athlete's recent activities.

**Parameters:**
- `limit` (int, default: 10): Maximum number of activities to return

**Returns:** List of activities with distance, pace, time, elevation, etc.

### `get_activities_by_date_range`
Get activities within a specific date range.

**Parameters:**
- `start_date` (str): Start date in ISO format (YYYY-MM-DD)
- `end_date` (str): End date in ISO format (YYYY-MM-DD)
- `limit` (int, default: 30): Maximum number of activities to return

### `get_activity_by_id`
Get detailed information about a specific activity.

**Parameters:**
- `activity_id` (int): ID of the activity to retrieve

### `get_recent_activities`
Get activities from the past X days.

**Parameters:**
- `days` (int, default: 7): Number of days to look back
- `limit` (int, default: 10): Maximum number of activities to return

### `get_activity_streams`
Get time-series stream data for a specific activity.

**Parameters:**
- `activity_id` (int): ID of the activity
- `stream_types` (str, default: "heartrate,pace"): Comma-separated list of stream types
  - Available: heartrate, pace, altitude, cadence, distance, moving, temperature, time, watts

## Training Report Tools

### `get_training_report`
Get a comprehensive training report with recent running data.

**Parameters:**
- `refresh` (bool, default: True): Whether to fetch latest data from Strava first

**Returns:**
- `overall_summary`: Total runs, distance, time, elevation, avg pace, avg HR
- `weekly_summaries`: Per-week breakdown with date range and stats
- `individual_runs`: List of runs with date, name, distance, pace, HR, laps

## Training Plan Tools

These tools manage training plans stored locally.

### `save_training_plan`
Save a training plan. Claude should translate user's text description into JSON format first.

**Parameters:**
- `plan_json` (str): JSON string containing the training plan data
- `plan_id` (str, optional): Plan ID (generated if not provided)

**Returns:** `{"plan_id": "...", "saved": true}`

### `list_training_plans`
List all saved training plans with summary info.

**Returns:** List of plans with id, name, race date, is_active

### `get_training_plan`
Get a training plan by ID.

**Parameters:**
- `plan_id` (str): The plan ID to retrieve

**Returns:** Full training plan data

### `update_training_plan`
Update an existing training plan.

**Parameters:**
- `plan_id` (str): The plan ID to update
- `updates_json` (str): JSON string with fields to update

### `delete_training_plan`
Delete a training plan.

**Parameters:**
- `plan_id` (str): The plan ID to delete

### `analyze_plan_adherence`
Compare planned workouts against actual runs from Strava.

**Parameters:**
- `plan_id` (str): The plan ID to analyze

**Returns:**
- `completion_rate`: Percentage of planned workouts completed
- `completed_workouts`: List of completed workouts with planned vs actual
- `missed_workouts`: List of missed workouts
- `upcoming_workouts`: List of upcoming workouts (next 7 days)

## Coaching Tools

These tools provide coaching memory and context persistence.

### `get_coaching_context`
Load coaching context at the start of a coaching conversation.

**Parameters:**
- `athlete_id` (str, default: "default"): Athlete identifier

**Returns:**
- `coaching_persona`: Instructions for how to behave as a coach (from coaching_persona.md)
- `athlete_profile`: Training preferences, goals, injury history
- `recent_notes`: Last 10 session notes
- `recent_adjustments`: Last 5 plan adjustments
- `active_plan`: Summary of the active training plan

Claude should adopt the persona defined in the coaching_persona.md file.

### `save_coaching_note`
Save a note to persist insights across conversations.

**Parameters:**
- `note_type` (str): Type of note
  - `session_summary`: Summary of a coaching conversation
  - `insight`: An observation about training
  - `adjustment`: Record of a plan change
- `content_json` (str): JSON with note content (summary, key_points, etc.)
- `athlete_id` (str, default: "default"): Athlete identifier

### `update_athlete_profile`
Update the athlete's profile with new information.

**Parameters:**
- `updates_json` (str): JSON with fields to update
  - `name`: Athlete's name
  - `training_preferences`: Dict of preferences
  - `goals`: List of goal objects
  - `injury_history`: List of injury records
  - `notes`: Free-form notes
- `athlete_id` (str, default: "default"): Athlete identifier

## Intended Workflows

### 1. Training Check-in
```
User: "How's my training going?"
Claude:
1. get_training_report() - get recent training data
2. Analyze the data and provide feedback
```

### 2. Import a Training Plan
```
User: "Here's my training plan: [text]"
Claude:
1. Translate text to JSON format per TRAINING_PLAN_FORMAT.md
2. save_training_plan(plan_json) - save the plan
3. Confirm saved and summarize
```

### 3. Coaching Session
```
User: "Let's do a coaching check-in"
Claude:
1. get_coaching_context() - load persona and history
2. get_training_report() - get recent data
3. Conduct coaching conversation (adopt persona)
4. save_coaching_note() - persist session summary
```

### 4. Plan Review and Adjustment
```
User: "Am I on track with my plan?"
Claude:
1. get_coaching_context() - get active plan info
2. analyze_plan_adherence(plan_id) - compare planned vs actual
3. Discuss adherence and any needed adjustments
4. If adjustments made: update_training_plan() + save_coaching_note()
```

## CLI Commands

The package also provides CLI commands:

- `strava-mcp-server` - Start the MCP server
- `strava-analyze-plan [plan_id]` - Analyze training plan adherence
- `strava-generate-report` - Generate training report from local data
- `strava-generate-calendar [plan_id]` - Generate HTML calendar visualization
- `strava-update-data` - Update local run data from Strava

## Data Storage

Data is stored in the project root by default:
- `run_data/` - Cached run data from Strava
- `training_plans/` - Saved training plans
- `coaching_data/` - Coaching memory (persona, profile, notes)

Set `STRAVA_DATA_DIR` environment variable to change the data location.
