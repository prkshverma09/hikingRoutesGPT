from __future__ import annotations

import json
import os
from typing import List, Tuple, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pathlib import Path

from app.utils import (
    ors_hiking_route_with_waypoints,
    ExternalAPIError,
)
from app.library import generate_leaflet_map_html_from_geojson

# Load environment variables
load_dotenv()

router = APIRouter()

# Templates directory for the UI module
_templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/ui/coords", response_class=HTMLResponse)
async def coords_form(request: Request):
    return templates.TemplateResponse("coords_form.html", {"request": request})


@router.post("/ui/coords", response_class=HTMLResponse)
async def coords_form_submit(
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

    coords: List[Tuple[float, float]] = []
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

    start = snapped_waypoints[0] if snapped_waypoints else coords[0]
    # Auto-generate a clean title from summary (AI-like naming)
    distance_km = (summary.get("distance_m") or 0) / 1000.0
    duration_h = (summary.get("duration_s") or 0) / 3600.0
    auto_title = f"Scenic Trail • {distance_km:.1f} km • ~{duration_h:.1f} h"
    html = generate_leaflet_map_html_from_geojson(
        route_geojson,
        waypoints=snapped_waypoints or coords,
        title=auto_title,
    )
    return HTMLResponse(content=html)
