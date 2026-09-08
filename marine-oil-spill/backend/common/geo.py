"""
Shared geo utilities.

Every module converts between pixel space and lat/lon using the same
simple equirectangular mapping, driven by the bounding box stored in a
scene's meta.json (see docs/API_CONTRACT.md). Keeping this in one place
means all five modules agree on how coordinates are derived.
"""
from __future__ import annotations
import math


def pixel_to_lonlat(row: int, col: int, height: int, width: int, bounds: dict) -> tuple[float, float]:
    """
    bounds = {"min_lon", "max_lon", "min_lat", "max_lat"}
    Row 0 is the TOP of the image (north), consistent with how images are
    stored/read throughout this pipeline.
    """
    lon = bounds["min_lon"] + (col / max(width - 1, 1)) * (bounds["max_lon"] - bounds["min_lon"])
    lat = bounds["max_lat"] - (row / max(height - 1, 1)) * (bounds["max_lat"] - bounds["min_lat"])
    return lon, lat


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km between two lon/lat points."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing_deg(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Initial compass bearing (0=N, 90=E) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination_point(lon: float, lat: float, bearing_deg_: float, distance_km: float) -> tuple[float, float]:
    """Move from (lon,lat) along a bearing (deg) for distance_km. Returns (lon, lat)."""
    R = 6371.0
    br = math.radians(bearing_deg_)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(distance_km / R) + math.cos(p1) * math.sin(distance_km / R) * math.cos(br))
    l2 = l1 + math.atan2(
        math.sin(br) * math.sin(distance_km / R) * math.cos(p1),
        math.cos(distance_km / R) - math.sin(p1) * math.sin(p2),
    )
    return math.degrees(l2), math.degrees(p2)
