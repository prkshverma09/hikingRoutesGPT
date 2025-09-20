from typing import Iterable, Tuple, List, Optional, Protocol
import os
import json
from dotenv import load_dotenv


class WaypointLike(Protocol):
    name: str
    coordinates: Tuple[float, float]


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


def generate_leaflet_map_html_from_geojson(
    route_geojson: dict,
    waypoints: Iterable[Tuple[float, float]] | None = None,
    os_api_key: Optional[str] = None,
    title: str = "Hiking Route",
) -> str:
    """
    Generate a standalone HTML page rendering the provided GeoJSON FeatureCollection
    (LineString/MultiLineString) with an Outdoor-style cartography (OpenTopo default,
    CyclOSM/OSM/OS Raster toggles, hillshade overlay, route casing+line, arrows),
    and optional numbered markers for waypoints.
    """
    # Resolve OS API key from env if not provided
    if os_api_key is None:
        load_dotenv()
        os_api_key = os.getenv("OS_API_KEY")

    # Deduce a reasonable start center
    start_lat = 51.5
    start_lon = -0.1
    try:
        feats = route_geojson.get("features") or []
        if feats:
            geom = feats[0].get("geometry", {})
            gtype = geom.get("type")
            coords = geom.get("coordinates", [])
            if gtype == "LineString" and coords:
                start_lon, start_lat = coords[0]
            elif gtype == "MultiLineString" and coords and coords[0]:
                start_lon, start_lat = coords[0][0]
    except Exception:
        pass

    waypoints_js = []
    if waypoints:
        waypoints_js = [[lat, lon] for (lat, lon) in waypoints]

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>{title}</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\"/>
  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
  <script src=\"https://unpkg.com/leaflet-polylinedecorator@1.7.0/dist/leaflet.polylineDecorator.min.js\"></script>
  <style>
    html, body {{ height: 100%; margin: 0; }}
    #map {{ width: 100%; height: 100vh; }}
    .marker-badge {{
      background: #1f2937; color: #fff; border: 2px solid #0ea5e9;
      width: 28px; height: 28px; border-radius: 999px; display: grid; place-items: center;
      font: 700 12px/1 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    }}
  </style>
  </head>
  <body>
  <div id=\"map\"></div>
  <script>
    const startLat = {start_lat};
    const startLon = {start_lon};
    const route = {json.dumps(route_geojson)};
    const waypoints = {json.dumps(waypoints_js)};
    const osKey = {json.dumps(os_api_key)};

    const map = L.map('map', {{ zoomControl: true }}).setView([startLat, startLon], 13);

    // Base layers
    const osRaster = L.tileLayer(`https://api.os.uk/maps/raster/v1/zxy/Light_3857/{{z}}/{{x}}/{{y}}.png?key=${{osKey}}`, {{
      attribution: '© Ordnance Survey', maxZoom: 19
    }});
    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
    }});
    const openTopo = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 17,
      attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
    }});
    const cyclosm = L.tileLayer('https://{{s}}.tile-cyclosm.openstreetmap.fr/cyclosm/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 20, attribution: '&copy; OpenStreetMap contributors | Layer: CyclOSM'
    }});

    // Optional hillshade overlay (ESRI World Hillshade)
    const hillshade = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Hillshade/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles &copy; Esri', opacity: 0.35
    }});

    const baseLayers = {{ 'OpenTopoMap': openTopo, 'CyclOSM': cyclosm, 'OS Raster': osRaster, 'OpenStreetMap': osm }};
    const overlays = {{ 'Hillshade': hillshade }};
    openTopo.addTo(map);
    L.control.layers(baseLayers, overlays, {{ position: 'topright', collapsed: true }}).addTo(map);

    // Route: casing + main line
    const routeCasing = L.geoJSON(route, {{ style: {{ color: '#ffffff', weight: 8, opacity: 0.85, lineCap: 'round', lineJoin: 'round' }} }}).addTo(map);
    const routeLine = L.geoJSON(route, {{ style: {{ color: '#7a0f2b', weight: 6, opacity: 0.95, lineCap: 'round', lineJoin: 'round' }} }}).addTo(map);

    // Direction arrows
    try {{
      const layers = routeLine.getLayers ? routeLine.getLayers() : [];
      const segments = [];
      layers.forEach(l => {{
        const latlngs = l.getLatLngs();
        if (latlngs && latlngs.length) {{
          if (Array.isArray(latlngs[0])) {{ latlngs.forEach(seg => segments.push(L.polyline(seg))); }}
          else {{ segments.push(L.polyline(latlngs)); }}
        }}
      }});
      segments.forEach(seg => {{
        L.polylineDecorator(seg, {{
          patterns: [
            {{ offset: 25, repeat: 200, symbol: L.Symbol.arrowHead({{ pixelSize: 10, polygon: false, pathOptions: {{ stroke: true, color: '#111827', weight: 3, opacity: 0.9 }} }}) }}
          ]
        }}).addTo(map);
      }});
    }} catch (e) {{}}

    // Waypoint markers (numbered)
    try {{
      if (Array.isArray(waypoints)) {{
        waypoints.forEach(function (pt, idx) {{
          if (Array.isArray(pt) && pt.length === 2) {{
            const icon = L.divIcon({{ className: 'marker-badge', html: String(idx + 1) }});
            L.marker([pt[0], pt[1]], {{ icon }}).addTo(map);
          }}
        }});
      }}
    }} catch (e) {{}}

    // Fit bounds to route and markers
    try {{
      const group = L.featureGroup([routeCasing, ...waypoints.map(pt => L.marker([pt[0], pt[1]]))]);
      const bounds = group.getBounds();
      if (bounds && bounds.isValid()) map.fitBounds(bounds.pad(0.12));
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


def generate_leaflet_map_html_from_waypoints(
    waypoints: Iterable[WaypointLike],
    os_api_key: Optional[str] = None,
    title: str = "Custom Coordinates Map",
    show_markers: bool = True,
) -> str:
    """
    Generate map HTML from a sequence of Waypoint-like objects with
    attributes: name: str and coordinates: (lat, lon).
    """
    points: List[Tuple[float, float]] = [
        (float(w.coordinates[0]), float(w.coordinates[1])) for w in waypoints
    ]
    return generate_leaflet_map_html(points, os_api_key=os_api_key, title=title, show_markers=show_markers)
