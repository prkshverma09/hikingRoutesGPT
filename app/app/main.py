import os
import json
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .utils import geocode_os_names, generate_loop_coordinates, ors_hiking_route, geojson_to_gpx, ExternalAPIError

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
    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "start_lat": lat,
            "start_lon": lon,
            "route_geojson": json.dumps(route_geojson),
            "os_api_key": os_api_key,
            "title": f"Hike from {start_name}",
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
            "route_geojson": json.dumps(route_geojson),
            "os_api_key": os_api_key,
            "title": "Custom Coordinates Map",
        },
    )
