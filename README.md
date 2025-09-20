# Hiking Routes Service

A small FastAPI service that:

- Geocodes a start location using the Ordnance Survey Names API
- Generates a simple loop hiking route using OpenRouteService (foot-hiking)
- Returns the route as GeoJSON or GPX
- Renders a simple Leaflet map with OS raster tiles

## Requirements

- Python 3.10+
- API keys:
  - OS Names API key (environment: `OS_API_KEY`)
  - OpenRouteService API key (environment: `ORS_API_KEY`)

## Install

```bash
python -m venv app/.venv
source app/.venv/bin/activate
pip install -r app/requirements.txt
```

### Configure environment variables (.env)

You can use a `.env` file instead of exporting environment variables manually:

1) Copy the example file and fill in your keys:

```bash
cp .env.example .env
```

2) Edit `.env` and set the values for `OS_API_KEY` and `ORS_API_KEY`.

## Run the server

```bash
uvicorn --app-dir app app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Endpoints

- POST `/route` – Generate a route and return start coords + GeoJSON
- POST `/gpx` – Generate a route and return GPX
- POST `/gpx-from-geojson` – Convert provided GeoJSON to GPX
- GET `/map` – Render a Leaflet map with the generated route

### POST /route

Request body:

```json
{
  "start_name": "Southampton Central Station",
  "prompt": "9-mile circular hike from Southampton Central along the River Itchen",
  "offset_lat": 0.02,
  "offset_lon": 0.05
}
```

Example:

```bash
curl -X POST http://localhost:8000/route \
  -H 'Content-Type: application/json' \
  -d '{
    "start_name": "Southampton Central Station",
    "prompt": "9-mile circular hike from Southampton Central along the River Itchen"
  }'
```

### POST /gpx

Returns `application/gpx+xml` content.

```bash
curl -X POST http://localhost:8000/gpx \
  -H 'Content-Type: application/json' \
  -d '{
    "start_name": "Southampton Central Station"
  }' -o route.gpx
```

### POST /gpx-from-geojson

```bash
curl -X POST http://localhost:8000/gpx-from-geojson \
  -H 'Content-Type: application/json' \
  -d @geojson.json
```

Where `geojson.json` is of the form:

```json
{ "data": { "type": "FeatureCollection", "features": [...] } }
```

### GET /map

Open in a browser:

- http://localhost:8000/map?start_name=Southampton%20Central%20Station

You can tweak the loop shape via query parameters:

- `offset_lat` (default 0.02)
- `offset_lon` (default 0.05)

Example:

- http://localhost:8000/map?start_name=Southampton%20Central%20Station&offset_lat=0.02&offset_lon=0.05

## Running tests

```bash
pytest -q app/tests
```

## Notes

- This service currently forms a simple loop by offsetting the end point and returning to the start. For production, integrate more advanced loop generation using ORS isochrones or custom heuristics respecting target distance/elevation.
- The OS raster tiles require the `OS_API_KEY` and will be visible in the client-side map request URL. This is typical for public raster/XYZ tiles.
- A `.gitignore` is included to prevent committing `.env` and local venv files. Do not commit your real `.env`.
