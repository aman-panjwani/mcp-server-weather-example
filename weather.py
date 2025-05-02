from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server with the name "weather"
mcp = FastMCP("weather")

# Constants for NWS API base URL and user-agent header
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    Sends an asynchronous HTTP GET request to the National Weather Service (NWS) API.

    Args:
        url (str): The full API endpoint URL to fetch data from.

    Returns:
        dict[str, Any] | None: Parsed JSON response as a dictionary if successful;
        returns None if the request fails due to network errors or invalid responses.
    
    Notes:
        - Custom headers including a User-Agent are set to comply with NWS API requirements.
        - Uses a timeout of 30 seconds.
        - Catches and silences all exceptions to ensure graceful failure.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """
    Formats a single weather alert feature from the NWS API into a readable text block.

    Args:
        feature (dict): A dictionary representing a single alert from the API.

    Returns:
        str: A human-readable string containing the event type, area affected, severity,
             description, and any instructions.
    
    Notes:
        - Uses `.get()` with fallback defaults to handle missing keys safely.
    """
    props = feature["properties"]
    return f"""
        Event: {props.get('event', 'Unknown')}
        Area: {props.get('areaDesc', 'Unknown')}
        Severity: {props.get('severity', 'Unknown')}
        Description: {props.get('description', 'No description available')}
        Instructions: {props.get('instruction', 'No specific instructions provided')}
        """

@mcp.tool()
async def get_alerts(state: str) -> str:
    """
    Retrieves active weather alerts for a specified U.S. state.

    Args:
        state (str): Two-letter U.S. state code (e.g., "CA", "NY").

    Returns:
        str: A formatted string of weather alerts or a message indicating no alerts or errors.
    
    Workflow:
        1. Builds the alert endpoint URL using the state code.
        2. Fetches alert data using the `make_nws_request` helper.
        3. Formats each alert with `format_alert()` if any are present.
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    Retrieves a 7-day weather forecast for a given geographic coordinate.

    Args:
        latitude (float): Latitude of the desired location.
        longitude (float): Longitude of the desired location.

    Returns:
        str: A formatted string summarizing the forecast for the next five time periods.

    Workflow:
        1. Requests the gridpoint forecast metadata from the NWS using /points/{lat,long}.
        2. Extracts the forecast URL from the metadata.
        3. Fetches the full forecast data from the extracted URL.
        4. Parses and formats the forecast for up to the next 5 periods.
    
    Notes:
        - Handles both missing gridpoint and forecast data with fallback messages.
        - Only displays a limited number of periods for readability.
    """
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
            {period['name']}:
            Temperature: {period['temperature']}°{period['temperatureUnit']}
            Wind: {period['windSpeed']} {period['windDirection']}
            Forecast: {period['detailedForecast']}
            """
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

if __name__ == "__main__":
    # Starts the FastMCP server using stdio transport for message exchange
    mcp.run(transport='stdio')
