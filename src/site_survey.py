#!/usr/bin/env python3
"""
Site-survey math helpers: turning easy-to-measure inputs into the
bearing_deg / perp_distance_ft / line_bearing_deg / along_line_*_ft /
height_ft fields a site profile's line_obstructions and arc_obstructions
actually need (see docs/SITE_PROFILE_GUIDE.md).

You can always just measure bearing/distance/height directly in the
field and type them straight into scripts/build_site_profile.py -- this
module exists for the cases where that's harder than reading two points
off a map or a satellite image. Three independent techniques, each
useful on its own:

1. Two lat/lon points (e.g. read off Google Maps by right-clicking a
   point to get its coordinates) -> bearing_distance_ft() for a single
   point (arc obstruction reference point), or line_feature_from_points()
   for a pair of points defining a tree line's two ends.

2. Pixel coordinates on a screenshot, plus the map's zoom level -> the
   same two functions, fed with pixel-derived local offsets instead of
   lat/lon (see pixel_to_local_offset_ft() and
   scripts/map_pixel_to_geo.py, the CLI wrapper around this). This is
   the "share a screenshot with Claude" workflow: Claude reads pixel
   positions off the image you share, this module turns them into real
   bearing/distance/line geometry.

3. A shadow's length in a top-down (nadir) photo, plus the image's
   capture date/time -> shadow_height_ft(), using the Sun's actual
   elevation angle at that moment (via `ephem`, already a project
   dependency -- see src/sky_noise.py for the same library used for the
   Moon). This is the one technique here that can recover height from a
   purely top-down image; a nadir view has no other vertical information
   in it at all, so there's no shortcut around needing a shadow.

All distance/bearing math uses the same flat-earth approximation as
terrain.py's _offset_latlon -- adequate at the few-hundred-meter ranges
this project cares about (near-field obstructions), not for long-range
geodesy.
"""

import math
from datetime import datetime
from typing import Dict, Tuple

import ephem

FT_PER_M = 0.3048
EARTH_M_PER_DEG_LAT = 111320.0
WEB_MERCATOR_BASE_M_PER_PX = 156543.03392  # ground resolution at zoom 0, equator


# -- lat/lon-based measurement --------------------------------------

def latlon_to_local_offset_ft(lat0: float, lon0: float, lat1: float, lon1: float) -> Tuple[float, float]:
    """East/north offset (feet) of point 1 relative to point 0 -- the
    lat/lon counterpart to pixel_to_local_offset_ft(), for feeding
    line_feature_from_points() from two lat/lon points instead of two
    screenshot pixels."""
    east_m, north_m = _latlon_offset_m(lat0, lon0, lat1, lon1)
    return east_m / FT_PER_M, north_m / FT_PER_M


def bearing_distance_ft(lat0: float, lon0: float, lat1: float, lon1: float) -> Tuple[float, float]:
    """Compass bearing (degrees, 0=N/90=E) and distance (feet) from
    point 0 to point 1."""
    east_ft, north_ft = latlon_to_local_offset_ft(lat0, lon0, lat1, lon1)
    return _bearing_distance_from_en(east_ft, north_ft)


# -- pixel-based measurement (map screenshots) -----------------------

def meters_per_pixel(latitude_deg: float, zoom: int) -> float:
    """Web Mercator ground resolution (meters/pixel) at a given
    latitude and zoom level -- the standard formula behind Google
    Maps/Earth/OpenStreetMap tile scaling. `zoom` is the map's zoom
    level, visible in a Google Maps URL as the trailing 'z' in
    .../@42.735,-77.542,19z (19, here)."""
    return WEB_MERCATOR_BASE_M_PER_PX * math.cos(math.radians(latitude_deg)) / (2 ** zoom)


def pixel_to_local_offset_ft(pin_px: float, pin_py: float, target_px: float, target_py: float,
                              pin_lat: float, zoom: int) -> Tuple[float, float]:
    """East/north offset (feet) of a target pixel relative to a pin
    pixel on the SAME screenshot. Assumes standard image coordinates
    (x right, y down) and a north-up, non-tilted (straight-down
    satellite/map) view -- true of a default Google Maps/Earth view
    with no rotation, not true of an oblique "3D" street-level angle."""
    mpp = meters_per_pixel(pin_lat, zoom)
    east_m = (target_px - pin_px) * mpp
    north_m = -(target_py - pin_py) * mpp  # image y grows downward = south
    return east_m / FT_PER_M, north_m / FT_PER_M


def pixel_offset_to_bearing_distance(pin_px: float, pin_py: float, target_px: float, target_py: float,
                                      pin_lat: float, zoom: int) -> Tuple[float, float]:
    """Bearing (degrees) and distance (feet) from the pin to a target
    point, both given as pixel coordinates on the same screenshot."""
    east_ft, north_ft = pixel_to_local_offset_ft(pin_px, pin_py, target_px, target_py, pin_lat, zoom)
    return _bearing_distance_from_en(east_ft, north_ft)


# -- line-feature fitting (either lat/lon or pixel-derived points) ---

def line_feature_from_points(pin_east_ft: float, pin_north_ft: float,
                              end1_east_ft: float, end1_north_ft: float,
                              end2_east_ft: float, end2_north_ft: float) -> Dict[str, float]:
    """Fit a line_obstructions entry's geometry fields from three points
    in a shared local east/north-feet frame: the antenna (pin) and the
    line's two ends. Returns bearing_deg / perp_distance_ft /
    line_bearing_deg / along_line_start_ft / along_line_end_ft, matching
    terrain.py's TerrainProfile._line_feature_angle exactly (verified by
    tests/test_site_survey.py against that function directly) -- these
    four numbers plus height_ft are a complete line_obstructions entry.

    Use bearing_distance_ft()/pixel_to_local_offset_ft() to get each
    point's east/north-feet offset from the antenna first (pin's own
    offset is always (0, 0) relative to itself)."""
    ax, ay = end1_east_ft - pin_east_ft, end1_north_ft - pin_north_ft
    bx, by = end2_east_ft - pin_east_ft, end2_north_ft - pin_north_ft

    ab_x, ab_y = bx - ax, by - ay
    ab_len2 = ab_x * ab_x + ab_y * ab_y
    if ab_len2 < 1e-9:
        raise ValueError("The two line endpoints are the same point -- can't fit a line direction.")

    # Project the pin (origin) onto the line through A=(ax,ay), B=(bx,by).
    t = -(ax * ab_x + ay * ab_y) / ab_len2
    foot_x, foot_y = ax + t * ab_x, ay + t * ab_y

    bearing_deg, perp_distance_ft = _bearing_distance_from_en(foot_x, foot_y)

    line_bearing_deg, ab_len_ft = _bearing_distance_from_en(ab_x, ab_y)
    dir_x, dir_y = math.sin(math.radians(line_bearing_deg)), math.cos(math.radians(line_bearing_deg))

    along_start_ft = (ax - foot_x) * dir_x + (ay - foot_y) * dir_y
    along_end_ft = (bx - foot_x) * dir_x + (by - foot_y) * dir_y

    return {
        "bearing_deg": round(bearing_deg, 1),
        "perp_distance_ft": round(perp_distance_ft, 1),
        "line_bearing_deg": round(line_bearing_deg, 1),
        "along_line_start_ft": round(along_start_ft, 1),
        "along_line_end_ft": round(along_end_ft, 1),
    }


# -- shadow-length height estimation ---------------------------------

def shadow_height_ft(shadow_length_ft: float, lat: float, lon: float,
                      elevation_ft: float, capture_datetime_utc: datetime) -> Dict[str, float]:
    """Obstruction height from its shadow's length in a top-down
    (nadir) photo: height = shadow_length * tan(sun_elevation). A
    straight-down satellite/map image carries no other vertical
    information at all, so a visible shadow plus a known capture
    date/time is the one thing that can recover real height from it.

    capture_datetime_utc: when the image was actually taken, in UTC
    (naive datetime, treated as UTC) -- from the imagery's capture
    date/time. Google Earth Pro's historical-imagery view shows this
    (plain Google Maps screenshots usually don't carry it).

    Raises ValueError if the sun is too low (<0.5 deg) for a reliable
    estimate -- shadows get very long and small elevation-angle errors
    blow up the result near sunrise/sunset."""
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.elevation = elevation_ft * FT_PER_M
    obs.date = capture_datetime_utc
    sun = ephem.Sun()
    sun.compute(obs)
    sun_elevation_deg = math.degrees(sun.alt)
    sun_azimuth_deg = math.degrees(sun.az)

    if sun_elevation_deg <= 0.5:
        raise ValueError(
            f"Sun elevation at capture time is only {sun_elevation_deg:.1f} deg -- too low "
            "for a reliable shadow-length estimate (near sunrise/sunset or after dark, "
            "shadows get very long and small angle errors blow up the result)."
        )

    height_ft = shadow_length_ft * math.tan(math.radians(sun_elevation_deg))
    return {
        "height_ft": round(height_ft, 1),
        "sun_elevation_deg": round(sun_elevation_deg, 2),
        "sun_azimuth_deg": round(sun_azimuth_deg, 2),
    }


# -- internal ----------------------------------------------------------

def _latlon_offset_m(lat0: float, lon0: float, lat1: float, lon1: float) -> Tuple[float, float]:
    dlat_m = (lat1 - lat0) * EARTH_M_PER_DEG_LAT
    dlon_m = (lon1 - lon0) * EARTH_M_PER_DEG_LAT * math.cos(math.radians(lat0))
    return dlon_m, dlat_m  # (east_m, north_m)


def _bearing_distance_from_en(east: float, north: float) -> Tuple[float, float]:
    """Bearing (deg) and magnitude, from an (east, north) vector in any
    consistent linear unit -- returns the magnitude in whatever unit was
    passed in (feet in, feet out; meters in, meters out)."""
    distance = math.hypot(east, north)
    bearing_deg = math.degrees(math.atan2(east, north)) % 360.0
    return bearing_deg, distance
