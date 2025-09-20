import os
import json
import re
import builtins
import importlib

import pytest

from app.library import generate_leaflet_map_html, write_leaflet_map_html


@pytest.fixture
def sample_coords():
    return [
        (51.713, -0.786),
        (51.7125, -0.787),
        (51.712, -0.788),
    ]


def test_generate_leaflet_map_html_basic(sample_coords, monkeypatch):
    # Ensure no OS key -> falls back to OSM tiles
    monkeypatch.delenv("OS_API_KEY", raising=False)
    html = generate_leaflet_map_html(sample_coords, os_api_key=None, title="Test Map")

    # Basic structure
    assert "<!DOCTYPE html>" in html
    assert "unpkg.com/leaflet" in html  # Leaflet assets included
    assert "Test Map" in html

    # Contains map container and script
    assert "<div id=\"map\"></div>" in html

    # Uses either OS tiles (if .env provides key) or OSM tiles otherwise
    assert ("tile.openstreetmap.org" in html) or ("api.os.uk" in html)

    # Route GeoJSON should include our coords as [lon, lat]
    assert "\"coordinates\"" in html
    # Check first coordinate mapping (lon, lat order)
    assert "[-0.786, 51.713]" in html


def test_generate_leaflet_map_html_with_os_key(sample_coords, monkeypatch):
    # Simulate OS key in environment
    monkeypatch.setenv("OS_API_KEY", "dummy-os-key")
    html = generate_leaflet_map_html(sample_coords, os_api_key=None, title="OS Tiles")

    # Should use OS tiles
    assert "api.os.uk/maps/raster/v1/zxy/Light_3857" in html
    assert "dummy-os-key" in html


def test_write_leaflet_map_html_writes_file(sample_coords, tmp_path, monkeypatch):
    # Either OS or OSM tiles are acceptable depending on environment
    monkeypatch.delenv("OS_API_KEY", raising=False)
    out = tmp_path / "route.html"
    write_leaflet_map_html(sample_coords, str(out), os_api_key=None, title="File Test")

    assert out.exists()
    data = out.read_text(encoding="utf-8")
    assert "File Test" in data
    assert ("tile.openstreetmap.org" in data) or ("api.os.uk" in data)
    assert "[-0.787, 51.7125]" in data


def test_generate_leaflet_map_html_requires_two_points(monkeypatch):
    monkeypatch.delenv("OS_API_KEY", raising=False)
    with pytest.raises(ValueError):
        generate_leaflet_map_html([(51.0, -1.0)], os_api_key=None)
