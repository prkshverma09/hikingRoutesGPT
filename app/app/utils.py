import os
import json
from typing import Dict, Any, List, Tuple

import requests
from pyproj import Transformer


class ExternalAPIError(RuntimeError):
    pass


def _decode_polyline(encoded: str, precision: int = 5):
    """Decode a polyline to a list of (lat, lon) tuples. Supports precision 5 or 6."""
    coordinates = []
    index = 0
    lat = 0
    lon = 0
    factor = 10 ** precision

    while index < len(encoded):
        result = 1
        shift = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1f:
                break
        dlat = ~(result >> 1) if result & 1 else (result >> 1)
        lat += dlat

        result = 1
        shift = 0
        while True:
            b = ord(encoded[index]) - 63 - 1
            index += 1
            result += b << shift
            shift += 5
            if b < 0x1f:
                break
        dlon = ~(result >> 1) if result & 1 else (result >> 1)
        lon += dlon

        coordinates.append((lat / factor, lon / factor))

    return coordinates


def geocode_os_names(query: str, os_api_key: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Geocode a place name using Ordnance Survey Names API.

    Returns: (lat, lon, raw_entry)
    """
    url = "https://api.os.uk/search/names/v1/find"
    # Use default OSGB36 / British National Grid from API and convert to WGS84 here
    params = {"query": query, "key": os_api_key}
    r = requests.get(url, params=params, timeout=20)
    try:
        r.raise_for_status()
    except Exception as e:
        raise ExternalAPIError(f"OS Names API error: {e}")

    data = r.json()
    if not data.get("results"):
        raise ExternalAPIError("No geocoding results from OS Names API")

    entry = data["results"][0]["GAZETTEER_ENTRY"]
    x = float(entry["GEOMETRY_X"])  # typically BNG easting
    y = float(entry["GEOMETRY_Y"])  # typically BNG northing

    # If values look like easting/northing (outside lon/lat bounds), transform from EPSG:27700 -> EPSG:4326
    if abs(x) > 180 or abs(y) > 90:
        transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(x, y)
    else:
        lon, lat = x, y
    return lat, lon, entry


def generate_loop_coordinates(lat: float, lon: float, offset_lat: float, offset_lon: float) -> List[List[float]]:
    """
    Create a simple loop by offsetting from the start and returning to it.
    Returns coordinates in [lon, lat] pairs.
    """
    end_lat = lat + offset_lat
    end_lon = lon + offset_lon
    return [[lon, lat], [end_lon, end_lat], [lon, lat]]


def ors_hiking_route(coordinates: List[List[float]], ors_api_key: str) -> Dict[str, Any]:
    """
    Call OpenRouteService hiking directions and return GeoJSON FeatureCollection.
    """
    url = "https://api.openrouteservice.org/v2/directions/foot-hiking"
    headers = {"Authorization": ors_api_key, "Content-Type": "application/json"}
    payload = {
        "coordinates": coordinates,
        "instructions": True,
        "format": "geojson",
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=40)
    try:
        r.raise_for_status()
    except Exception as e:
        # Try to surface ORS error message
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise ExternalAPIError(f"ORS API error: {e}. Details: {err}")
    return r.json()


def geojson_to_gpx(geojson_data: Dict[str, Any]) -> str:
    """
    Convert a GeoJSON FeatureCollection or Feature with LineString/MultiLineString to GPX string.
    """
    # Extract coordinates from first LineString-like geometry
    def extract_coords(feature: Dict[str, Any]) -> List[List[float]]:
        geom = feature.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])
        if gtype == "LineString":
            return coords
        if gtype == "MultiLineString" and coords:
            # flatten first linestring
            return coords[0]
        raise ValueError("Unsupported GeoJSON geometry for GPX conversion")

    coords = None
    # Support ORS directions JSON by converting it to a coordinates list
    if "routes" in geojson_data and geojson_data["routes"]:
        geom = geojson_data["routes"][0].get("geometry")
        if isinstance(geom, dict) and geom.get("coordinates"):
            coords = geom["coordinates"]
        elif isinstance(geom, str):
            # Try decoding encoded polyline with precision 5, then 6
            try:
                latlon = _decode_polyline(geom, precision=5)
            except Exception:
                latlon = _decode_polyline(geom, precision=6)
            # Convert (lat, lon) -> [lon, lat]
            coords = [[lon, lat] for lat, lon in latlon]
        else:
            raise ValueError("Unsupported ORS geometry for GPX conversion")
    else:
        features = geojson_data.get("features")
        if features:
            coords = extract_coords(features[0])
        else:
            # It might be a single Feature
            if geojson_data.get("type") == "Feature":
                coords = extract_coords(geojson_data)
            else:
                raise ValueError("Invalid GeoJSON for GPX conversion")

    gpx_header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="HikingRoutesGPT" xmlns="http://www.topografix.com/GPX/1/1">\n'
        "<trk>\n<trkseg>\n"
    )
    gpx_footer = "</trkseg>\n</trk>\n</gpx>\n"

    parts = [gpx_header]
    for lon, lat in coords:
        parts.append(f'  <trkpt lat="{lat}" lon="{lon}"></trkpt>\n')
    parts.append(gpx_footer)
    return "".join(parts)
