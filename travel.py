import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    prompt = """
You are a cycling route planner.

Task:
- Create a cycling route near {area}.
- Route type: {route_type} (one of: "loop", "out-and-back").
- Number of waypoints (including start/end): {num_points}.
- Maximum total distance: {max_distance_km} km (approximate).
- If provided, start at: {start_name or null} with coordinates {start_lat, start_lng or null}.
- Prefer bike-friendly paths, parks, and scenic points.

Output requirements:
- Return ONLY a valid JSON array. No explanations, no markdown, no trailing text.
- Each element must strictly follow:
  { "name": string, "coordinates": [latitude: number, longitude: number] }
- Waypoints must be ordered in ride sequence.
- If route_type is "loop", last waypoint should equal the first.
- Keep all points plausibly within/near {area} and consistent geographically.
- Use decimal degrees for coordinates (latitude first, then longitude).
- Do not include duplicate consecutive points.

Example shape (for illustration only; do not echo this example):
[
  {
    "name": "Place A",
    "coordinates": [51.5794, -0.3371]
  }
]

Now produce the JSON for: {area}.
"""

    result = await runner.run(
        input=prompt,
        model="openai/gpt-4.1",
        mcp_servers=[
            "joerup/exa-mcp",        # For semantic travel research
            "tsion/brave-search-mcp", # For travel information search
        ]
    )

    print(f"Travel Planning Results:\n{result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
