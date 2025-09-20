import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from .library import generate_leaflet_map_html_from_waypoints
from .types import Waypoint
import json

def build_hiking_prompt(
    area: str,
    route_type: str,
    num_points: int,
    max_distance_km: float,
    start_name: str | None = None,
    start_lat: float | None = None,
    start_lng: float | None = None,
) -> str:
    start_line = (
        f"- If provided, start at: {start_name} with coordinates {start_lat}, {start_lng}."
        if start_name is not None and start_lat is not None and start_lng is not None
        else "- If provided, start at: null with coordinates null."
    )

    return (
        f"""
You are a hiking route planner.

Task:
- Create a hiking route near {area}.
- Route type: {route_type} (one of: "loop", "out-and-back").
- Number of waypoints (including start/end): {num_points}.
- Maximum total distance: {max_distance_km} km (approximate).
{start_line}
- Prefer bike-friendly paths, parks, and scenic points.

Output requirements:
- Return ONLY a valid JSON array. No explanations, no markdown, no trailing text.
- Each element must strictly follow:
  {{ "name": string, "coordinates": [latitude: number, longitude: number] }}
- Waypoints must be ordered in ride sequence.
- If route_type is "loop", last waypoint should equal the first.
- Keep all points plausibly within/near {area} and consistent geographically.
- Use decimal degrees for coordinates (latitude first, then longitude).
- Do not include duplicate consecutive points.

Example shape (for illustration only; do not echo this example):
[
  {{
    "name": "Place A",
    "coordinates": [51.5794, -0.3371]
  }}
]

Now produce the JSON for: {area}.
"""
    )

def build_map_html_from_result(final_output: str) -> str:
    """Parse JSON final_output into Waypoints and return Leaflet map HTML."""
    waypoint_objs = [
        Waypoint(
            name=w["name"],
            coordinates=(float(w["coordinates"][0]), float(w["coordinates"][1]))
        )
        for w in json.loads(final_output)
    ]
    return generate_leaflet_map_html_from_waypoints(waypoint_objs)

load_dotenv()

async def generate_travel_map_html(
    area: str,
    route_type: str,
    num_points: int,
    max_distance_km: float,
) -> str:
    # Import here so the module can be imported even if dedalus_labs isn't installed
    from dedalus_labs import AsyncDedalus, DedalusRunner
    # Read API key from env / .env
    # Explicitly try both repo-root .env and app/.env
    try:
        repo_root = Path(__file__).resolve().parents[2]
        app_dir = Path(__file__).resolve().parents[1]
        load_dotenv(dotenv_path=repo_root / ".env")
        load_dotenv(dotenv_path=app_dir / ".env")
    except Exception:
        load_dotenv()
    api_key = os.getenv("DEDALUS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing DEDALUS_API_KEY. Please set it in your environment or .env file."
        )
    client = AsyncDedalus(api_key=api_key)
    runner = DedalusRunner(client)
    prompt = build_hiking_prompt(
        area=area,
        route_type=route_type,
        num_points=num_points,
        max_distance_km=max_distance_km,
        start_name=None,
        start_lat=None,
        start_lng=None,
    )
    result = await runner.run(
        input=prompt,
        model="openai/gpt-4.1",
        mcp_servers=[
            "joerup/exa-mcp",
            "tsion/brave-search-mcp",
        ],
    )
    return build_map_html_from_result(result.final_output)

async def main():
    html = await generate_travel_map_html(
        area="Harrow, London",
        route_type="loop",
        num_points=8,
        max_distance_km=25,
    )
    with open("app/travel.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    # Ensure lazy import path also works when running as a module
    try:
        asyncio.run(main())
    except ModuleNotFoundError as e:
        if "dedalus_labs" in str(e):
            raise SystemExit(
                "dedalus_labs is not installed in the current interpreter.\n"
                "Activate your venv and install requirements, then run:\n"
                "  source .venv/bin/activate && python -m pip install -r requirements.txt && python -m app.app.travel\n"
                "Or run directly with the venv python:\n"
                "  .venv/bin/python -m app.app.travel"
            )
        raise
