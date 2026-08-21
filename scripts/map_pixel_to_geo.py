#!/usr/bin/env python3
"""
Turn pixel coordinates on a map screenshot into the bearing_deg /
perp_distance_ft (and, for a line, line_bearing_deg / along_line_*_ft)
fields a site profile obstruction needs. See docs/SITE_PROFILE_GUIDE.md
("Building a profile from a map screenshot, with Claude") for the full
workflow this supports: share a screenshot in your conversation, have
Claude read off the pixel coordinates of the pin and each obstruction,
then run this script (or have Claude run it) with those numbers.

Two modes:

  point  -- one obstruction reference point (for an arc_obstructions
            cluster, or the near point of a line). Outputs bearing_deg
            and perp_distance_ft/distance_ft.

  line   -- two points marking a tree line's/row's two ends. Outputs a
            complete line_obstructions geometry: bearing_deg,
            perp_distance_ft, line_bearing_deg, along_line_start_ft,
            along_line_end_ft.

You need the pin's actual latitude (for the Web Mercator ground-scale
correction) and the map's zoom level (the trailing 'z' in a Google Maps
URL, e.g. .../@42.735,-77.542,19z -> zoom 19). Pixel coordinates are
standard image coordinates: x right, y down, (0,0) at the image's
top-left corner -- easiest to read directly off the image file's pixel
grid (e.g. by opening it in any image viewer/editor that shows a cursor
position) or have Claude estimate them from the shared screenshot.

This assumes a north-up, straight-down (nadir) view with no rotation or
3D tilt -- the default view in Google Maps/Earth, not an oblique "3D"
angle.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import site_survey as ss


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=['point', 'line'], required=True)
    ap.add_argument('--pin-lat', type=float, required=True, help="Antenna/pin latitude, decimal degrees")
    ap.add_argument('--zoom', type=int, required=True, help="Map zoom level (the trailing 'z' in the URL)")
    ap.add_argument('--pin-px', type=float, required=True)
    ap.add_argument('--pin-py', type=float, required=True)

    ap.add_argument('--target-px', type=float, help="[point mode] the obstruction reference point")
    ap.add_argument('--target-py', type=float)

    ap.add_argument('--end1-px', type=float, help="[line mode] one end of the row")
    ap.add_argument('--end1-py', type=float)
    ap.add_argument('--end2-px', type=float, help="[line mode] the other end of the row")
    ap.add_argument('--end2-py', type=float)

    ap.add_argument('--height-ft', type=float,
                     help="Optional -- if given, included in the printed JSON snippet ready to paste "
                          "into the profile (still need to add it yourself if you skip this)")
    ap.add_argument('--name', default=None, help="Optional obstruction name for the JSON snippet")
    args = ap.parse_args()

    if args.mode == 'point':
        if args.target_px is None or args.target_py is None:
            ap.error("point mode needs --target-px and --target-py")
        bearing_deg, distance_ft = ss.pixel_offset_to_bearing_distance(
            args.pin_px, args.pin_py, args.target_px, args.target_py, args.pin_lat, args.zoom)
        print(f"bearing_deg:   {bearing_deg:.1f}")
        print(f"distance_ft:   {distance_ft:.1f}")
        print()
        print("For an arc_obstructions entry, distance_ft above is your 'distance_ft' and you'll")
        print("still need to estimate az_start_deg/az_end_deg (the angular width of the cluster)")
        print("-- run this again for the left and right edges of the cluster to get a bearing for")
        print("each, and use those as az_start_deg/az_end_deg.")
        if args.height_ft is not None:
            snippet = {
                "name": args.name or "TODO",
                "az_start_deg": round(bearing_deg, 1),
                "az_end_deg": round(bearing_deg, 1),
                "distance_ft": round(distance_ft, 1),
                "height_ft": args.height_ft,
            }
            print()
            print("Starter arc_obstructions snippet (fix az_start_deg/az_end_deg by hand):")
            print(json.dumps(snippet, indent=2))

    else:
        missing = [n for n, v in [('--end1-px', args.end1_px), ('--end1-py', args.end1_py),
                                   ('--end2-px', args.end2_px), ('--end2-py', args.end2_py)] if v is None]
        if missing:
            ap.error(f"line mode needs {', '.join(missing)}")

        pin_e, pin_n = 0.0, 0.0
        e1_e, e1_n = ss.pixel_to_local_offset_ft(args.pin_px, args.pin_py, args.end1_px, args.end1_py,
                                                   args.pin_lat, args.zoom)
        e2_e, e2_n = ss.pixel_to_local_offset_ft(args.pin_px, args.pin_py, args.end2_px, args.end2_py,
                                                   args.pin_lat, args.zoom)
        geom = ss.line_feature_from_points(pin_e, pin_n, e1_e, e1_n, e2_e, e2_n)

        for k, v in geom.items():
            print(f"{k}: {v}")

        snippet = dict(geom)
        snippet["name"] = args.name or "TODO"
        if args.height_ft is not None:
            snippet["height_ft"] = args.height_ft
        else:
            snippet["height_ft"] = "TODO"
        # Put name/height first for readability when pasted into the profile.
        ordered = {"name": snippet.pop("name"), "height_ft": snippet.pop("height_ft"), **snippet}
        print()
        print("line_obstructions snippet (paste into your profile, fix height_ft/name if needed):")
        print(json.dumps(ordered, indent=2))


if __name__ == '__main__':
    main()
