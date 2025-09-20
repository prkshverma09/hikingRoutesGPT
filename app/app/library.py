from typing import Iterable, Tuple, List, Optional
import os
import json
from dotenv import load_dotenv


def generate_leaflet_map_html(
    coordinates: Iterable[Tuple[float, float]],
    os_api_key: Optional[str] = None,
    title: str = "Custom Coordinates Map",
    show_markers: bool = True,
) -> str:
    """
    Generate a standalone HTML page (as a string) containing a Leaflet map with a
    polyline drawn through the provided coordinates.

    Args:
        coordinates: Iterable of (lat, lon) pairs
        os_api_key: If provided, use Ordnance Survey raster tiles; if None, use OSM tiles
        title: Page title

    Returns:
        HTML string
    """
    points: List[Tuple[float, float]] = list(coordinates)
    if len(points) < 2:
        raise ValueError("Provide at least two coordinates to draw a line")

    # Resolve OS API key from env if not provided
    if os_api_key is None:
        # Load from .env if present
        load_dotenv()
        os_api_key = os.getenv("OS_API_KEY")

    # Build GeoJSON LineString with [lon, lat] ordering
    coords_lonlat = [[lon, lat] for lat, lon in points]
    route_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords_lonlat},
                "properties": {},
            }
        ],
    }

    start_lat, start_lon = points[0]

    if os_api_key:
        tile_js = f"""
  // OS Raster Tiles
  L.tileLayer(`https://api.os.uk/maps/raster/v1/zxy/Light_3857/{{z}}/{{x}}/{{y}}.png?key={os_api_key}`, {{
    attribution: '© Ordnance Survey',
    maxZoom: 19
  }}).addTo(map);
"""
    else:
        tile_js = """
  // OpenStreetMap Tiles (fallback if no OS key)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);
"""

    # Prepare a JS-safe waypoints array [[lat, lon], ...]
    waypoints_js = json.dumps([[lat, lon] for (lat, lon) in points])

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{title}</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\"/>
  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
  <style>
    html, body {{ height: 100%; margin: 0; }}
    #map {{ width: 100%; height: 100vh; }}
  </style>
  </head>
  <body>
  <div id=\"map\"></div>
  <script>
    const startLat = {start_lat};
    const startLon = {start_lon};
    const route = {json.dumps(route_geojson)};
    const waypoints = {waypoints_js};

    const map = L.map('map').setView([startLat, startLon], 13);
{tile_js}
    // Route GeoJSON
    const layer = L.geoJSON(route, {{
      style: {{ color: 'blue', weight: 4 }}
    }}).addTo(map);

    // Optional markers for waypoints
    {("waypoints.forEach(pt => L.marker(pt).addTo(map));" if show_markers else "")}

    // Fit map to route if possible
    try {{
      const bounds = layer.getBounds();
      if (bounds && bounds.isValid()) {{
        map.fitBounds(bounds.pad(0.1));
      }}
    }} catch (e) {{}}
  </script>
  </body>
  </html>
"""
    return html


def write_leaflet_map_html(
    coordinates: Iterable[Tuple[float, float]],
    output_file: str,
    os_api_key: Optional[str] = None,
    title: str = "Custom Coordinates Map",
    show_markers: bool = True,
) -> None:
    """
    Write a standalone HTML file with a Leaflet map that draws a polyline for the
    provided coordinates.
    """
    html = generate_leaflet_map_html(coordinates, os_api_key=os_api_key, title=title, show_markers=show_markers)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
