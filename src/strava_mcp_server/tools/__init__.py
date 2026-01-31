"""MCP tools for the Strava MCP Server."""

from strava_mcp_server.tools.activities import register_activity_tools
from strava_mcp_server.tools.reports import register_report_tools
from strava_mcp_server.tools.training_plans import register_training_plan_tools
from strava_mcp_server.tools.coaching import register_coaching_tools

__all__ = [
    "register_activity_tools",
    "register_report_tools",
    "register_training_plan_tools",
    "register_coaching_tools",
]


def register_all_tools(mcp, strava_client):
    """Register all MCP tools with the server."""
    register_activity_tools(mcp, strava_client)
    register_report_tools(mcp, strava_client)
    register_training_plan_tools(mcp)
    register_coaching_tools(mcp)
