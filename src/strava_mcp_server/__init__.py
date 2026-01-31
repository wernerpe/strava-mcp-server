"""Strava MCP Server package."""

from strava_mcp_server.server import main
from strava_mcp_server.strava_client import StravaClient

__all__ = ["main", "StravaClient"]
