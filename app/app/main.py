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
import sys
# Ensure project root is on sys.path to import root-level packages like `ui`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
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
        # Extract lat/lon from the first LineString or MultiLineString
        features = route_geojson.get("features") or []
        if not features:
            raise ValueError("No features in ORS response")
        geom = features[0].get("geometry", {})
        gtype = geom.get("type")
        glines = geom.get("coordinates", [])
        latlon: List[tuple[float, float]] = []
        if gtype == "LineString":
            latlon = [(c[1], c[0]) for c in glines]
        elif gtype == "MultiLineString":
            for seg in glines:
                latlon.extend((c[1], c[0]) for c in seg)
        else:
            raise ValueError("Unsupported geometry type for HTML generation")
        html = generate_leaflet_map_html(latlon, title=f"Hike from {start_name}")
    except ExternalAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return HTMLResponse(content=html)


class Point(BaseModel):
    lat: float
    lon: float


class CoordsPayload(BaseModel):
    coordinates: List[Point] = Field(..., description="Array of points in order to draw a polyline")


@app.post("/map-from-coords")
def map_from_coords(request: Request, payload: CoordsPayload):
    if not payload.coordinates or len(payload.coordinates) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two coordinates to draw a line")

    latlon = [(p.lat, p.lon) for p in payload.coordinates]
    try:
        html = generate_leaflet_map_html(latlon, title="Custom Coordinates Map")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to build map: {e}")
    return HTMLResponse(content=html)


# -----------------------------
# Simple UI for entering coordinates
# -----------------------------
from ui.router import router as ui_router
app.include_router(ui_router)
