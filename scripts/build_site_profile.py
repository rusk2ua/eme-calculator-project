#!/usr/bin/env python3
"""
Interactive wizard for building a site profile JSON (see
docs/SITE_PROFILE_GUIDE.md) -- walks through location, elevation,
obstructions, and receiver noise figures, auto-fetching what it can
from USGS EPQS, and writes a ready-to-use profile under
data/site_profiles/. Ends by validating the result and offering to
generate the polar plots immediately so you can eyeball the obstruction
wedge before trusting it.

Run it and answer the prompts:
    python3 scripts/build_site_profile.py

Every question has a sensible default shown in [brackets] -- press
Enter to accept it. Ctrl+C at any point aborts cleanly without writing
anything.

For obstructions, you can enter the geometry three ways: type
bearing/distance numbers directly (if you've already measured them or
already have them from scripts/map_pixel_to_geo.py or
scripts/estimate_shadow_height.py), give two lat/lon points and let the
wizard compute the geometry, or give two pixel points from a map
screenshot (same math as map_pixel_to_geo.py, just inline).
"""

import json
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from eme_calculator import EMECalculator
import site_survey as ss
import terrain as terrain_module
from terrain import TerrainProfile

STANDARD_BANDS = [144, 432, 902, 1296, 2304, 3456, 5760, 10368]


# -- small prompt helpers ---------------------------------------------

def ask(prompt, default=None, required=False):
    suffix = f" [{default}]" if default not in (None, "") else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if raw:
            return raw
        if default not in (None, ""):
            return default
        if not required:
            return ""
        print("  This one's required -- try again.")


def ask_float(prompt, default=None, required=False):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw:
            if default is not None:
                return default
            if not required:
                return None
            print("  This one's required -- try again.")
            continue
        try:
            return float(raw)
        except ValueError:
            print("  Not a number -- try again.")


def ask_yes_no(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer y or n.")


def ask_choice(prompt, choices, default):
    choice_str = "/".join(c if c != default else c.upper() for c in choices)
    while True:
        raw = input(f"{prompt} [{choice_str}]: ").strip().lower()
        if not raw:
            return default
        for c in choices:
            if raw == c or raw == c[0]:
                return c
        print(f"  Please answer one of: {', '.join(choices)}")


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "site"


def hr(title):
    print()
    print(f"--- {title} " + "-" * max(0, 50 - len(title)))


# -- obstruction geometry entry ----------------------------------------

def enter_line_geometry(pin_lat, pin_lon):
    method = ask_choice(
        "How do you want to enter this row's position?",
        ["manual", "latlon", "pixel"], "manual")

    if method == "manual":
        perp_distance_ft = ask_float("Perpendicular distance from the antenna to the row's nearest point (ft)",
                                      required=True)
        bearing_deg = ask_float("Compass bearing from the antenna to that nearest point (deg)", required=True)
        line_bearing_deg = ask_float(
            "Compass bearing the row itself runs along (e.g. 0=N-S row, 90=E-W row)", required=True)
        geom = {"bearing_deg": bearing_deg, "perp_distance_ft": perp_distance_ft,
                "line_bearing_deg": line_bearing_deg}
        if ask_yes_no("Is the row centered on that nearest point (same length in both directions)?", True):
            geom["half_length_ft"] = ask_float("Half-length (ft, extends this far each way)", required=True)
        else:
            print("  Offsets are measured from the nearest point, in the line_bearing_deg direction "
                  "(negative = the opposite direction).")
            geom["along_line_start_ft"] = ask_float("Start offset (ft)", required=True)
            geom["along_line_end_ft"] = ask_float("End offset (ft)", required=True)
        return geom

    print("  Enter the row's two ends.")
    if method == "latlon":
        e1lat = ask_float("  End 1 latitude", required=True)
        e1lon = ask_float("  End 1 longitude", required=True)
        e2lat = ask_float("  End 2 latitude", required=True)
        e2lon = ask_float("  End 2 longitude", required=True)
        e1 = ss.latlon_to_local_offset_ft(pin_lat, pin_lon, e1lat, e1lon)
        e2 = ss.latlon_to_local_offset_ft(pin_lat, pin_lon, e2lat, e2lon)
    else:
        zoom = int(ask_float("  Map zoom level (the trailing 'z' in the Google Maps URl)", required=True))
        pin_px = ask_float("  Pin pixel X", required=True)
        pin_py = ask_float("  Pin pixel Y", required=True)
        e1px = ask_float("  End 1 pixel X", required=True)
        e1py = ask_float("  End 1 pixel Y", required=True)
        e2px = ask_float("  End 2 pixel X", required=True)
        e2py = ask_float("  End 2 pixel Y", required=True)
        e1 = ss.pixel_to_local_offset_ft(pin_px, pin_py, e1px, e1py, pin_lat, zoom)
        e2 = ss.pixel_to_local_offset_ft(pin_px, pin_py, e2px, e2py, pin_lat, zoom)

    geom = ss.line_feature_from_points(0.0, 0.0, e1[0], e1[1], e2[0], e2[1])
    print(f"  -> bearing_deg={geom['bearing_deg']}, perp_distance_ft={geom['perp_distance_ft']}, "
          f"line_bearing_deg={geom['line_bearing_deg']}, "
          f"along_line_start_ft={geom['along_line_start_ft']}, along_line_end_ft={geom['along_line_end_ft']}")
    return geom


def enter_arc_geometry(pin_lat, pin_lon):
    method = ask_choice(
        "How do you want to enter this cluster's position?",
        ["manual", "latlon", "pixel"], "manual")

    if method == "manual":
        az_start_deg = ask_float("Azimuth span start (deg)", required=True)
        az_end_deg = ask_float("Azimuth span end (deg)", required=True)
        distance_ft = ask_float("Representative distance (ft)", required=True)
        return {"az_start_deg": az_start_deg, "az_end_deg": az_end_deg, "distance_ft": distance_ft}

    print("  Enter the cluster's left and right edges (or just one point twice for a narrow cluster).")
    if method == "latlon":
        e1lat = ask_float("  Left edge latitude", required=True)
        e1lon = ask_float("  Left edge longitude", required=True)
        e2lat = ask_float("  Right edge latitude", required=True)
        e2lon = ask_float("  Right edge longitude", required=True)
        b1, d1 = ss.bearing_distance_ft(pin_lat, pin_lon, e1lat, e1lon)
        b2, d2 = ss.bearing_distance_ft(pin_lat, pin_lon, e2lat, e2lon)
    else:
        zoom = int(ask_float("  Map zoom level", required=True))
        pin_px = ask_float("  Pin pixel X", required=True)
        pin_py = ask_float("  Pin pixel Y", required=True)
        e1px = ask_float("  Left edge pixel X", required=True)
        e1py = ask_float("  Left edge pixel Y", required=True)
        e2px = ask_float("  Right edge pixel X", required=True)
        e2py = ask_float("  Right edge pixel Y", required=True)
        b1, d1 = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, e1px, e1py, pin_lat, zoom)
        b2, d2 = ss.pixel_offset_to_bearing_distance(pin_px, pin_py, e2px, e2py, pin_lat, zoom)

    az_start_deg, az_end_deg = min(b1, b2), max(b1, b2)
    distance_ft = (d1 + d2) / 2.0
    print(f"  -> az_start_deg={az_start_deg:.1f}, az_end_deg={az_end_deg:.1f}, distance_ft={distance_ft:.1f}")
    print("  (Check this span doesn't wrap past 360 -- if your cluster straddles due north, enter it manually instead.)")
    return {"az_start_deg": round(az_start_deg, 1), "az_end_deg": round(az_end_deg, 1),
            "distance_ft": round(distance_ft, 1)}


def build_line_obstruction(pin_lat, pin_lon):
    hr("Line obstruction (tree row, hedge, fence)")
    name = ask("Name", required=True)
    description = ask("Description (optional)")
    height_ft = ask_float("Height above ground at the antenna (ft)", required=True)
    geom = enter_line_geometry(pin_lat, pin_lon)
    entry = {"name": name}
    if description:
        entry["description"] = description
    entry["height_ft"] = height_ft
    entry.update(geom)
    return entry


def build_arc_obstruction(pin_lat, pin_lon):
    hr("Arc obstruction (tree cluster / stand)")
    name = ask("Name", required=True)
    description = ask("Description (optional)")
    height_ft = ask_float("Height above ground at the antenna (ft)", required=True)
    geom = enter_arc_geometry(pin_lat, pin_lon)
    entry = {"name": name}
    if description:
        entry["description"] = description
    entry.update(geom)
    entry["height_ft"] = height_ft
    return entry


# -- validation ----------------------------------------------------------

def validate_profile(path):
    hr("Validating")
    tp = TerrainProfile(path)
    angles = [tp.horizon_angle_deg(az) for az in range(0, 360, 2)]
    print(f"Obstruction horizon ranges {min(angles):.1f}° to {max(angles):.1f}° across all azimuths.")
    if max(angles) < 0.5:
        print("  Nothing registers as an obstruction anywhere -- fine for a genuinely clear site, "
              "otherwise double check your entries.")

    warnings = []
    for feat in tp.profile.get("line_obstructions", []):
        label = feat.get("name", "(unnamed line)")
        if feat.get("height_ft", 0) <= 0:
            warnings.append(f"{label}: height_ft should be positive")
        if feat.get("perp_distance_ft", 0) <= 0:
            warnings.append(f"{label}: perp_distance_ft should be positive")
    for feat in tp.profile.get("arc_obstructions", []):
        label = feat.get("name", "(unnamed cluster)")
        if feat.get("height_ft", 0) <= 0:
            warnings.append(f"{label}: height_ft should be positive")
        if feat.get("distance_ft", 0) <= 0:
            warnings.append(f"{label}: distance_ft should be positive")
        az0, az1 = feat.get("az_start_deg"), feat.get("az_end_deg")
        if az0 is not None and az1 is not None and az0 >= az1:
            warnings.append(f"{label}: az_start_deg ({az0}) should be less than az_end_deg ({az1})")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("No obvious problems found.")
    return tp


# -- main ------------------------------------------------------------------

def main():
    print(__doc__)
    hr("Basic info")
    profile = {"profile_name": ask("Profile name (e.g. 'K2UA - Springwater, NY')", required=True)}

    hr("Location")
    if ask_yes_no("Enter location as a Maidenhead grid square (instead of lat/lon directly)?", False):
        grid = ask("Grid square (6-10 chars, e.g. FN12fr46wo)", required=True)
        lat, lon = EMECalculator().maidenhead_to_latlon(grid)
        print(f"  -> {lat:.6f}, {lon:.6f}")
        if not ask_yes_no("Use these coordinates?", True):
            lat = ask_float("Latitude (decimal degrees)", required=True)
            lon = ask_float("Longitude (decimal degrees)", required=True)
        profile["grid_square"] = grid
    else:
        lat = ask_float("Latitude (decimal degrees)", required=True)
        lon = ask_float("Longitude (decimal degrees)", required=True)
        grid_guess = ask("Grid square (optional, informational only)")
        if grid_guess:
            profile["grid_square"] = grid_guess
    profile["latitude"] = lat
    profile["longitude"] = lon

    hr("Elevation")
    elevation_ft = None
    if ask_yes_no("Auto-fetch site elevation from USGS EPQS? (needs internet)", True):
        try:
            elevation_ft = terrain_module.fetch_elevation_ft(lat, lon)
            print(f"  -> {elevation_ft:.2f} ft ASL")
            profile["elevation_source"] = (
                f"USGS National Map Elevation Point Query Service (EPQS), queried {date.today()}")
        except Exception as e:
            print(f"  Fetch failed ({e}) -- enter manually.")
    if elevation_ft is None:
        elevation_ft = ask_float("Site elevation (feet ASL)", required=True)
    profile["elevation_ft"] = elevation_ft
    profile["antenna_agl_ft"] = ask_float("Antenna height above ground level (ft)", default=10.0)

    notes = ask("Notes -- survey precision, date, anything useful to a future you (optional)")
    if notes:
        profile["notes"] = notes

    hr("Obstructions")
    print("Add every tree line, cluster, or other obstruction that matters. Answer 'done' when finished.")
    line_obstructions, arc_obstructions = [], []
    while True:
        kind = ask_choice("Add an obstruction?", ["line", "arc", "done"], "done")
        if kind == "done":
            break
        elif kind == "line":
            line_obstructions.append(build_line_obstruction(lat, lon))
        else:
            arc_obstructions.append(build_arc_obstruction(lat, lon))
    if line_obstructions:
        profile["line_obstructions"] = line_obstructions
    if arc_obstructions:
        profile["arc_obstructions"] = arc_obstructions

    hr("Receiver noise figures")
    print("Per band, at the antenna feedpoint (before feedline loss, after the preamp). "
          "Blank to skip a band -- it'll fall back to a generic placeholder table.")
    nf = {}
    for band in STANDARD_BANDS:
        val = ask_float(f"  {band} MHz noise figure (dB)")
        if val is not None:
            nf[str(band)] = val
    if nf:
        nf["_meta"] = f"Entered via build_site_profile.py, {date.today()}"
        profile["receiver_noise_figure_db"] = nf

    hr("Regional terrain floor")
    if ask_yes_no("Auto-fetch the 8-compass-octant DEM terrain floor from USGS EPQS? (needs internet)", True):
        try:
            samples = terrain_module.fetch_octant_samples(lat, lon)
            samples["_meta"] = f"USGS EPQS, queried {date.today()}"
            profile["dem_octant_samples_ft"] = samples
            print("  -> fetched.")
        except Exception as e:
            print(f"  Fetch failed ({e}) -- skipping. Azimuths without a near-field obstruction above "
                  "will default to a flat 0° floor; you can add dem_octant_samples_ft by hand later.")

    hr("Save")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "site_profiles")
    os.makedirs(out_dir, exist_ok=True)
    default_filename = slugify(profile["profile_name"]) + ".json"
    filename = ask("Output filename", default=default_filename)
    out_path = os.path.normpath(os.path.join(out_dir, filename))
    if os.path.exists(out_path) and not ask_yes_no(f"{out_path} already exists -- overwrite?", False):
        print("Aborted without writing.")
        return
    with open(out_path, "w") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")
    print(f"Wrote {out_path}")

    validate_profile(out_path)

    hr("Plots")
    if ask_yes_no("Generate the polar plots now so you can eyeball the obstruction wedge?", True):
        band = int(ask_float("Band (MHz)", default=1296.0))
        plot_out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "plots_" + slugify(profile["profile_name"]))
        gen_script = os.path.join(os.path.dirname(__file__), "generate_polar_plots.py")
        cmd = [sys.executable, gen_script, "--profile", out_path, "--band", str(band),
               "--start-date", f"{date.today().year}-01-01", "--days", "365",
               "--out-dir", plot_out_dir,
               "--tables-out", os.path.join(plot_out_dir, "monthly_conditions.md")]
        print("Running: " + " ".join(cmd))
        subprocess.run(cmd, check=False)
        print(f"Plots written to {plot_out_dir} -- open them and check the gray wedge matches what you'd "
              "expect standing at the site (see docs/SITE_PROFILE_GUIDE.md if it doesn't).")

    print()
    print("Done. Next: python3 src/eme_calculator.py --profile " + out_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted -- nothing more was written.")
        sys.exit(1)
