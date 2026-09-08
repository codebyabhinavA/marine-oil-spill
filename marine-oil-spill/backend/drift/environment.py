"""
M3 helper — backend/drift/environment.py

Synthetic ocean current + wind field so hindcasting.py has something to
backtrack against without needing a live metocean API (e.g. Copernicus
Marine, NOAA OSCAR) wired up yet. Swap `get_environment_at` for a real
API call later — the function signature is the contract.

Returns a steady-ish current (typical of a regional current in the demo
area) with a small oscillating component so the drift track isn't a
perfectly straight line, which is what real currents look like locally.
"""
from __future__ import annotations
import math


def get_environment_at(lon: float, lat: float, hours_before_now: float) -> dict:
    """
    Returns {"current_speed_kmh", "current_bearing_deg",
             "wind_speed_kmh", "wind_bearing_deg"} at the given point/time.

    current_bearing_deg / wind_bearing_deg follow compass convention
    (direction the water/wind is FLOWING TOWARD, 0=N, 90=E) so callers can
    feed them straight into common.geo.destination_point.
    """
    base_current_bearing = 205.0  # roughly SW-flowing regional current
    oscillation = 15.0 * math.sin(hours_before_now / 6.0)
    current_bearing = (base_current_bearing + oscillation) % 360
    current_speed = 1.3 + 0.4 * math.sin(hours_before_now / 4.0)  # km/h, gentle variation

    wind_bearing = (current_bearing + 20) % 360
    wind_speed = 12.0 + 3.0 * math.cos(hours_before_now / 5.0)  # km/h

    return {
        "current_speed_kmh": round(current_speed, 3),
        "current_bearing_deg": round(current_bearing, 2),
        "wind_speed_kmh": round(wind_speed, 3),
        "wind_bearing_deg": round(wind_bearing, 2),
    }
