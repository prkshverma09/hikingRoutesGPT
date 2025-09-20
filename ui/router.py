from __future__ import annotations

import json
import os
from typing import List, Tuple, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pathlib import Path

from app.travel import generate_travel_map_html
import asyncio

# Load environment variables
load_dotenv()

router = APIRouter()

# Templates directory for the UI module
_templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/ui/coords", response_class=HTMLResponse)
async def coords_form(request: Request):
    return templates.TemplateResponse("coords_form.html", {"request": request})


def _parse_instructions(text: str) -> dict:
    """Parse free-form text like 'area: Lake District; route_type: loop; num_points: 8; max_distance_km: 25; start_name: Keswick; start_lat: 54.6; start_lng: -3.1; ...'.
    Returns a dict with parsed fields and leftover prompt_text (unparsed lines).
    """
    fields = {
        "area": None,
        "route_type": None,
        "num_points": None,
        "max_distance_km": None,
        "start_name": None,
        "start_lat": None,
        "start_lng": None,
        "prompt_text": "",
    }
    leftovers: list[str] = []
    # Accept separators: newlines or semicolons
    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts.extend([p.strip() for p in line.split(";") if p.strip()])

    for part in parts:
        if ":" in part:
            key, val = part.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            try:
                if key == "area":
                    fields["area"] = val
                elif key == "route_type":
                    v = val.lower()
                    fields["route_type"] = v if v in {"loop", "out-and-back", "outandback", "out_back"} else val
                elif key == "num_points":
                    fields["num_points"] = int(float(val))
                elif key in {"max_distance", "max_distance_km"}:
                    fields["max_distance_km"] = float(val)
                elif key == "start_name":
                    fields["start_name"] = val
                elif key in {"start_lat", "start_latitude"}:
                    fields["start_lat"] = float(val)
                elif key in {"start_lng", "start_lon", "start_longitude"}:
                    fields["start_lng"] = float(val)
                else:
                    leftovers.append(part)
            except Exception:
                leftovers.append(part)
        else:
            leftovers.append(part)

    # Normalize route_type values
    rt = fields["route_type"]
    if rt in {"outandback", "out_back"}:
        fields["route_type"] = "out-and-back"
    # Defaults if missing
    if not fields["area"]:
        fields["area"] = "Harrow, London"
    if not fields["route_type"]:
        fields["route_type"] = "loop"
    if not fields["num_points"]:
        fields["num_points"] = 8
    if not fields["max_distance_km"]:
        fields["max_distance_km"] = 25.0
    # Prompt text is leftover free-form lines joined
    fields["prompt_text"] = "\n".join(leftovers).strip()
    return fields


@router.post("/ui/coords", response_class=HTMLResponse)
async def coords_form_submit(
    request: Request,
    instructions: str = Form(...),
):
    """
    Accepts a single free-text instructions field. Parses keys like:
    area, route_type, num_points, max_distance_km, start_name, start_lat, start_lng.
    Remaining text is treated as additional preferences.
    """
    try:
        parsed = _parse_instructions(instructions)
        # Cap total time so UI never hangs indefinitely
        html = await asyncio.wait_for(
            generate_travel_map_html(
                area=parsed["area"],
                route_type=parsed["route_type"],
                num_points=parsed["num_points"],
                max_distance_km=parsed["max_distance_km"],
            ),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Planner timed out. Please try again or simplify the request.")
    except RuntimeError as e:
        # Likely missing API keys (e.g., DEDALUS_API_KEY)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate travel map: {e}")

    return HTMLResponse(content=html)
