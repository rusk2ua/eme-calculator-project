#!/usr/bin/env python3
"""
Terrain and obstruction horizon model for the EME Dish Siting Calculator.

Combines two kinds of data into a single azimuth-indexed "horizon angle"
function (the minimum elevation angle the Moon must clear at a given
azimuth to be usable from the site):

1. Near-field explicit obstructions (tree lines, tree clusters) that the
   station operator has measured or estimated -- these dominate close to
   the antenna and are usually far more limiting than anything a public
   DEM can see, because a 30-90m-resolution elevation dataset does not
   resolve individual trees or hedgerows.

2. A coarse regional "terrain floor" sampled from USGS's National Map
   Elevation Point Query Service (EPQS), used to fill in azimuths that
   have no explicit near-field feature and to sanity-check the far side
   of explicit features.

See README.md ("Methodology & Limitations") for the honest caveats on
what this does and does not capture -- most importantly, it is NOT a
dense ray-marched horizon profile. It is deliberately built from a
sparse set of DEM samples (see fetch_octant_samples / the cached
dem_octant_samples_ft block in a site profile) plus the operator's own
directional obstruction estimates.

Data sources
------------
USGS EPQS (public, no API key): https://epqs.nationalmap.gov/v1/json
  Documentation: https://apps.nationalmap.gov/epqs/

For a fuller, denser horizon profile than this module builds by default,
swap in one of:
  - py3dep (https://github.com/hyriver/py3dep) -- USGS 3DEP, 1-10m
    resolution over the US, much better tree-adjacent terrain fidelity.
  - elevation / srtm.py (SRTM 30-90m, global coverage) for sites outside
    the US 3DEP footprint.
  - AWS Terrain Tiles, public S3 bucket 'elevation-tiles-prod'
    (registry.opendata.aws/terrain-tiles) -- Terrarium-encoded PNG DEM
    tiles, good fit if you're already in an AWS-centric workflow.
Any of these can replace fetch_elevation_ft() below without touching the
rest of this module.
"""

import json
import math
from typing import Dict, List, Optional, Tuple

FT_PER_M = 0.3048
EARTH_M_PER_DEG_LAT = 111320.0


def fetch_elevation_ft(lat: float, lon: float, timeout: float = 10.0) -> float:
    """Fetch a single elevation point (feet) from USGS EPQS. Requires
    internet access on the machine this runs on. Not used at analysis
    time by default -- see fetch_octant_samples() for how the cached
    dem_octant_samples_ft values in a site profile were generated."""
    import urllib.parse
    import urllib.request

    params = urllib.parse.urlencode({
        "x": lon, "y": lat, "units": "Feet", "wkid": 4326, "includeDate": "false"
    })
    url = f"https://epqs.nationalmap.gov/v1/json?{params}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return float(data["value"])


def _offset_latlon(lat0: float, lon0: float, bearing_deg: float, dist_m: float) -> Tuple[float, float]:
    """Small-distance flat-earth offset -- adequate for the few-km ranges
    used here; do not use this for long-range geodesy."""
    b = math.radians(bearing_deg)
    dlat = dist_m * math.cos(b) / EARTH_M_PER_DEG_LAT
    dlon = dist_m * math.sin(b) / (EARTH_M_PER_DEG_LAT * math.cos(math.radians(lat0)))
    return lat0 + dlat, lon0 + dlon


def fetch_octant_samples(lat: float, lon: float, range_ft: float = 2000,
                          bearings: Optional[List[float]] = None) -> Dict[str, float]:
    """Regenerate the dem_octant_samples_ft block for a site profile by
    querying USGS EPQS on each principal bearing plus the site itself.
    Requires internet access. Returns a dict matching the profile's
    dem_octant_samples_ft schema (minus the _meta key)."""
    if bearings is None:
        bearings = [0, 45, 90, 135, 180, 225, 270, 315]
    samples = {"site_elevation_ft": round(fetch_elevation_ft(lat, lon), 2)}
    for b in bearings:
        plat, plon = _offset_latlon(lat, lon, b, range_ft * FT_PER_M)
        samples[str(int(b))] = round(fetch_elevation_ft(plat, plon), 2)
    return samples


class TerrainProfile:
    """Loads a site obstruction profile (see data/site_profiles/*.json)
    and answers: what elevation angle must the Moon be above, at a given
    azimuth, to be usable from an (optionally offset) antenna position?"""

    def __init__(self, profile_path: str):
        with open(profile_path, "r") as f:
            self.profile = json.load(f)

    @property
    def latitude(self) -> float:
        return self.profile["latitude"]

    @property
    def longitude(self) -> float:
        return self.profile["longitude"]

    @property
    def elevation_ft(self) -> float:
        return self.profile["elevation_ft"]

    @property
    def antenna_agl_ft(self) -> float:
        return self.profile.get("antenna_agl_ft", 0)

    def horizon_angle_deg(self, azimuth_deg: float,
                           offset_east_ft: float = 0.0,
                           offset_north_ft: float = 0.0) -> float:
        """Effective horizon elevation angle (degrees) at this azimuth,
        for an antenna moved offset_east_ft/offset_north_ft from the
        profile's reference location. This is the max() over every
        obstruction feature and the DEM terrain floor -- the nearest
        thing that actually blocks the sky wins, closer taller features
        override farther/shorter ones automatically because each
        contributes its own atan(height/distance) and we take the max."""
        az = azimuth_deg % 360.0
        candidates = [self._dem_floor_deg(az)]

        for feat in self.profile.get("line_obstructions", []):
            angle = self._line_feature_angle(feat, az, offset_east_ft, offset_north_ft)
            if angle is not None:
                candidates.append(angle)

        for feat in self.profile.get("arc_obstructions", []):
            angle = self._arc_feature_angle(feat, az)
            if angle is not None:
                candidates.append(angle)

        return max(candidates)

    # -- internal ---------------------------------------------------

    def _line_feature_angle(self, feat: dict, az_deg: float,
                             dx_ft: float, dy_ft: float) -> Optional[float]:
        """Ray-intersect azimuth az_deg against a straight line feature
        (e.g. a fencerow/treeline), accounting for antenna offset."""
        line_bearing = math.radians(feat["line_bearing_deg"])
        # Unit vector along the line, and the line's perpendicular
        # (normal) direction, both in local ENU (x=east, y=north).
        line_dir = (math.sin(line_bearing), math.cos(line_bearing))
        normal_bearing = math.radians(feat["bearing_deg"])
        # A point on the line: perp_distance_ft out along its normal
        # bearing from the *profile's reference* antenna position.
        px = feat["perp_distance_ft"] * math.sin(normal_bearing)
        py = feat["perp_distance_ft"] * math.cos(normal_bearing)

        # Antenna position in the same world frame as the line (the
        # profile's reference antenna position is the world origin).
        # Ray from the antenna along az_deg: antenna + t*(rdx,rdy).
        # Line: (px,py) + s*(lx,ly). Solve for t,s:
        #   [rdx -lx][t]   [px-dx_ft]
        #   [rdy -ly][s] = [py-dy_ft]
        az = math.radians(az_deg)
        rdx, rdy = math.sin(az), math.cos(az)
        lx, ly = line_dir
        bx, by = px - dx_ft, py - dy_ft

        det = rdx * (-ly) - (-lx) * rdy
        if abs(det) < 1e-9:
            return None  # ray parallel to the line
        t = (bx * (-ly) - (-lx) * by) / det
        s = (rdx * by - rdy * bx) / det

        if t <= 0:
            return None  # intersection behind the observer

        # Row extent along the line, measured from the perpendicular-foot
        # point (px,py) in the direction of line_dir (positive = toward
        # line_bearing, e.g. north for a line_bearing of 0). Prefer
        # explicit (possibly asymmetric) start/end bounds; fall back to
        # a symmetric half_length_ft for rows centered on the foot point.
        if "along_line_start_ft" in feat and "along_line_end_ft" in feat:
            lo = min(feat["along_line_start_ft"], feat["along_line_end_ft"])
            hi = max(feat["along_line_start_ft"], feat["along_line_end_ft"])
        else:
            lo, hi = -feat["half_length_ft"], feat["half_length_ft"]
        if s < lo or s > hi:
            return None  # beyond the end of the row

        distance_ft = t
        return math.degrees(math.atan2(feat["height_ft"], distance_ft))

    def _arc_feature_angle(self, feat: dict, az_deg: float) -> Optional[float]:
        """Flat-topped obstruction over an azimuth range, with a 3-degree
        linear taper at each edge so the horizon function doesn't step
        discontinuously (matches how a real tree cluster's silhouette
        tapers rather than ending in a cliff)."""
        taper = 3.0
        start, end = feat["az_start_deg"], feat["az_end_deg"]
        full_angle = math.degrees(math.atan2(feat["height_ft"], feat["distance_ft"]))

        def in_range(a):
            # handle wraparound if ever needed; our features don't cross 360
            return start <= a <= end

        if in_range(az_deg):
            # taper down near the edges
            edge_dist = min(az_deg - start, end - az_deg)
            if edge_dist < taper:
                return full_angle * (edge_dist / taper)
            return full_angle
        # just outside the range -- taper down to zero over `taper` degrees
        if start - taper <= az_deg < start:
            return full_angle * ((az_deg - (start - taper)) / taper)
        if end < az_deg <= end + taper:
            return full_angle * (((end + taper) - az_deg) / taper)
        return None

    def _dem_floor_deg(self, az_deg: float) -> float:
        samples = self.profile.get("dem_octant_samples_ft")
        if not samples:
            return 0.0
        site_elev = samples.get("site_elevation_ft", self.elevation_ft)
        bearings = sorted(int(k) for k in samples.keys() if k != "site_elevation_ft" and k != "_meta")
        if not bearings:
            return 0.0
        range_ft = 2000.0  # matches fetch_octant_samples default

        def angle_at(b):
            delta_ft = samples[str(b)] - site_elev
            return math.degrees(math.atan2(delta_ft, range_ft))

        # piecewise-linear interpolation around the compass, wrapping at 360
        n = len(bearings)
        for i in range(n):
            b0 = bearings[i]
            b1 = bearings[(i + 1) % n]
            span = (b1 - b0) % 360 or 360
            if (az_deg - b0) % 360 < span:
                frac = ((az_deg - b0) % 360) / span
                a0, a1 = angle_at(b0), angle_at(b1)
                return a0 + (a1 - a0) * frac
        return angle_at(bearings[0])
