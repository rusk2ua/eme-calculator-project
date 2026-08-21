#!/usr/bin/env python3
"""
Estimate an obstruction's height from its shadow's length in a top-down
(nadir) map/satellite image, using the Sun's actual elevation angle at
the moment the image was captured (via `ephem`). See
docs/SITE_PROFILE_GUIDE.md ("Building a profile from a map screenshot,
with Claude") for the full workflow.

A straight-down satellite/map image carries no other vertical
information at all -- there's no shortcut around needing a visible
shadow and a known capture date/time for this specific technique. If
you don't have both, just estimate height by eye (this project already
works to +/-5ft field-estimate precision, so a careful guess is
entirely consistent with everything else in a typical profile).

Where to get the capture date/time: Google Earth Pro's historical
imagery view shows it (click the clock icon / "Historical Imagery").
Plain Google Maps screenshots usually don't carry this -- if you don't
know it, this technique isn't usable for that image.

Measuring the shadow's length in feet: use scripts/map_pixel_to_geo.py
in point mode twice (once for the shadow's base at the obstruction,
once for the shadow's tip) and take the difference in distance_ft, or
convert a pixel length directly via site_survey.meters_per_pixel().
"""

import argparse
import sys
from datetime import datetime

sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'src'))
import site_survey as ss


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--shadow-length-ft', type=float, required=True)
    ap.add_argument('--lat', type=float, required=True)
    ap.add_argument('--lon', type=float, required=True)
    ap.add_argument('--elevation-ft', type=float, required=True, help="Site elevation, feet ASL")
    ap.add_argument('--capture-datetime-utc', required=True,
                     help="Image capture date/time in UTC, 'YYYY-MM-DD HH:MM' (24-hour). "
                          "If you only have a local time, convert to UTC first.")
    args = ap.parse_args()

    try:
        capture = datetime.strptime(args.capture_datetime_utc, '%Y-%m-%d %H:%M')
    except ValueError:
        ap.error("--capture-datetime-utc must look like '2026-06-21 16:00'")

    try:
        result = ss.shadow_height_ft(args.shadow_length_ft, args.lat, args.lon,
                                      args.elevation_ft, capture)
    except ValueError as e:
        print(f"Can't estimate from this capture time: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Sun elevation at capture:  {result['sun_elevation_deg']:.1f}°")
    print(f"Sun azimuth at capture:    {result['sun_azimuth_deg']:.1f}°  "
          f"(the shadow should point roughly {(result['sun_azimuth_deg'] + 180) % 360:.0f}° "
          f"from the obstruction -- opposite the sun; if the shadow you measured points somewhere "
          f"very different, double check the capture date/time)")
    print(f"Estimated height:          {result['height_ft']:.1f} ft")


if __name__ == '__main__':
    main()
