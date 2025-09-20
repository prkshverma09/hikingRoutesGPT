import os
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .utils import (
    geocode_os_names,
    generate_loop_coordinates,
    ors_hiking_route,
    geojson_to_gpx,
    ExternalAPIError,
    ors_hiking_route_with_waypoints,
)
from .library import generate_leaflet_map_html

app = FastAPI(title="Hiking Routes Service", version="0.1.0")

from pathlib import Path
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Load environment variables from .env if present
load_dotenv()


class RouteRequest(BaseModel):
    start_name: str = Field(..., description="Place name to start from (e.g., 'Southampton Central Station')")
    prompt: str | None = Field(None, description="Free-form prompt about the hike, currently unused but reserved")
    offset_lat: float = Field(0.02, description="Latitude offset to form a simple loop")
    offset_lon: float = Field(0.05, description="Longitude offset to form a simple loop")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/route")
def create_route(req: RouteRequest):
    os_api_key = os.getenv("OS_API_KEY")
    ors_api_key = os.getenv("ORS_API_KEY")
    if not os_api_key:
        raise HTTPException(status_code=500, detail="Missing OS_API_KEY environment variable")
    if not ors_api_key:
        raise HTTPException(status_code=500, detail="Missing ORS_API_KEY environment variable")

    try:
        lat, lon, _ = geocode_os_names(req.start_name, os_api_key)
        coords = generate_loop_coordinates(lat, lon, req.offset_lat, req.offset_lon)
        route_geojson = ors_hiking_route(coords, ors_api_key)
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return JSONResponse({
        "start": {"lat": lat, "lon": lon},
        "route": route_geojson,
    })


class GeoJSONPayload(BaseModel):
    data: Dict[str, Any]


@app.post("/gpx-from-geojson")
def gpx_from_geojson(payload: GeoJSONPayload):
    try:
        gpx = geojson_to_gpx(payload.data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert to GPX: {e}")
    return PlainTextResponse(content=gpx, media_type="application/gpx+xml")


@app.post("/gpx")
def gpx_for_route(req: RouteRequest):
    os_api_key = os.getenv("OS_API_KEY")
    ors_api_key = os.getenv("ORS_API_KEY")
    if not os_api_key:
        raise HTTPException(status_code=500, detail="Missing OS_API_KEY environment variable")
    if not ors_api_key:
        raise HTTPException(status_code=500, detail="Missing ORS_API_KEY environment variable")

    try:
        lat, lon, _ = geocode_os_names(req.start_name, os_api_key)
        coords = generate_loop_coordinates(lat, lon, req.offset_lat, req.offset_lon)
        route_geojson = ors_hiking_route(coords, ors_api_key)
        gpx = geojson_to_gpx(route_geojson)
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return PlainTextResponse(content=gpx, media_type="application/gpx+xml")


@app.get("/map")
def map_view(request: Request, start_name: str, offset_lat: float = 0.02, offset_lon: float = 0.05):
    os_api_key = os.getenv("OS_API_KEY")
    ors_api_key = os.getenv("ORS_API_KEY")
    if not os_api_key:
        raise HTTPException(status_code=500, detail="Missing OS_API_KEY environment variable")
    if not ors_api_key:
        raise HTTPException(status_code=500, detail="Missing ORS_API_KEY environment variable")

    try:
        lat, lon, _ = geocode_os_names(start_name, os_api_key)
        coords = generate_loop_coordinates(lat, lon, offset_lat, offset_lon)
        route_geojson = ors_hiking_route(coords, ors_api_key)
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    # Note: OS tiles key is exposed to client here; that's expected for raster tiles.
    # Build waypoints for markers as [[lat, lon], ...] from coords [[lon, lat], ...]
    waypoints_latlon = [[c[1], c[0]] for c in coords]

    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "start_lat": lat,
            "start_lon": lon,
            "route_geojson": route_geojson,
            "os_api_key": os_api_key,
            "title": f"Hike from {start_name}",
            "waypoints_json": waypoints_latlon,
        },
    )


class Point(BaseModel):
    lat: float
    lon: float


class CoordsPayload(BaseModel):
    coordinates: List[Point] = Field(..., description="Array of points in order to draw a polyline")


@app.post("/map-from-coords")
def map_from_coords(request: Request, payload: CoordsPayload):
    os_api_key = os.getenv("OS_API_KEY")
    if not os_api_key:
        raise HTTPException(status_code=500, detail="Missing OS_API_KEY environment variable")

    if not payload.coordinates or len(payload.coordinates) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two coordinates to draw a line")

    # Build GeoJSON FeatureCollection with a LineString
    coords_lonlat = [[p.lon, p.lat] for p in payload.coordinates]
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

    start = payload.coordinates[0]
    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "start_lat": start.lat,
            "start_lon": start.lon,
            "route_geojson": route_geojson,
            "os_api_key": os_api_key,
            "title": "Custom Coordinates Map",
            "waypoints_json": [[p.lat, p.lon] for p in payload.coordinates],
        },
    )


# -----------------------------
# Simple UI for entering coordinates
# -----------------------------
@app.get("/ui/coords", response_class=HTMLResponse)
def coords_form(request: Request):
    # Render a small HTML form to input coordinates
    return templates.TemplateResponse("coords_form.html", {"request": request})


@app.post("/ui/coords", response_class=HTMLResponse)
def coords_form_submit(
    request: Request,
    coords_text: str = Form(...),
):
    """
    Accepts coordinates as JSON in the textarea. Supported formats:
      - [[lat, lon], [lat, lon], ...]
      - [{"lat": 51.713, "lon": -0.786}, ...]
    """
    try:
        parsed = json.loads(coords_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(parsed, list) or len(parsed) < 2:
        raise HTTPException(status_code=400, detail="Provide a JSON array with at least two coordinates")

    coords: List[tuple[float, float]] = []
    for item in parsed:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            lat, lon = float(item[0]), float(item[1])
        elif isinstance(item, dict) and "lat" in item and "lon" in item:
            lat, lon = float(item["lat"]), float(item["lon"])
        else:
            raise HTTPException(status_code=400, detail=f"Invalid coordinate item: {item}")
        coords.append((lat, lon))

    # Always snap using ORS
    ors_api_key = os.getenv("ORS_API_KEY")
    if not ors_api_key:
        raise HTTPException(status_code=500, detail="Missing ORS_API_KEY environment variable")
    # Build an ORS directions request with all coordinates as waypoints
    coords_lonlat = [[lon, lat] for lat, lon in coords]
    try:
        route_geojson, snapped_waypoints, summary = ors_hiking_route_with_waypoints(coords_lonlat, ors_api_key)
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    # Render snapped line but mark only original input waypoints
    os_api_key = os.getenv("OS_API_KEY")
    if not os_api_key:
        raise HTTPException(status_code=500, detail="Missing OS_API_KEY environment variable")

    start = snapped_waypoints[0] if snapped_waypoints else coords[0]
    # Auto-generate a clean title from summary (AI-like naming)
    distance_km = (summary.get("distance_m") or 0) / 1000.0
    duration_h = (summary.get("duration_s") or 0) / 3600.0
    auto_title = f"Scenic Trail • {distance_km:.1f} km • ~{duration_h:.1f} h"
    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "start_lat": start[0],
            "start_lon": start[1],
            "route_geojson": route_geojson,
            "os_api_key": os_api_key,
            "title": auto_title,
            # Use snapped waypoint positions if available; otherwise original
            "waypoints_json": (
                [[lat, lon] for (lat, lon) in snapped_waypoints]
                if snapped_waypoints else [[lat, lon] for (lat, lon) in coords]
            ),
        },
    )
