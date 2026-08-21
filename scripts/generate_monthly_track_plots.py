#!/usr/bin/env python3
"""
Generate one polar plot PER MONTH showing every region's single BEST
(lowest EME degradation) day's actual pass track -- not the whole
year's scatter of qualifying days (that's generate_polar_plots.py).

Usage:
    python3 scripts/generate_monthly_track_plots.py \
        --profile data/site_profiles/k2ua_fn12fr46wo.json \
        --band 1296 --out-dir docs/plots/monthly_tracks

Each plot is a polar chart (elevation as radius, zenith at center,
horizon at the rim; azimuth as the angle, N at top, clockwise) covering
one calendar month. For every region that has a qualifying pass that
month, the SINGLE best (lowest-degradation) day's track is drawn as a
connected line from the moment the Moon enters that region's azimuth
window (above the band minimum elevation and the local terrain horizon)
to the moment it leaves -- a real ~10-60 degree sweep, not the whole
moonrise-to-moonset track and not the narrow day-to-day spread of just
the peak instant (see README Methodology & Limitations / Revision
History v2.2.0 for that distinction). Three points are marked and
elevation-labeled on every track: start (^), peak (*), end (v).

This is deliberately a SEPARATE, additive set of plots alongside
generate_polar_plots.py's annual per-region scatter plots -- that
script answers "what's the overall shape of the year for this region,"
this one answers "what does the single best pass actually look like."

Color: six regions overlaid on one chart is a "compare all pairs"
scenario (lines can cross/sit next to each other anywhere), which the
dataviz skill's validator confirms cannot clear the strict CVD floor for
more than ~3 categorical series -- this palette lands in the documented
"legal only with secondary encoding" band (worst-case CVD delta-E ~6,
normal-vision delta-E >=15). That's why every track also carries direct
region-name + elevation-value text labels and distinct marker SHAPES
(^/*/v) per phase of the pass: identity is never color-alone here.
"""

import argparse
import os
import sys
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from eme_calculator import EMECalculator
from terrain import TerrainProfile

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']

OBSTRUCTION_FILL = '#B0B0B0'
OBSTRUCTION_ALPHA = 0.55

# Validated 6-color categorical palette (dataviz skill, scripts/validate_palette.js,
# --pairs all): blue/yellow/aqua/magenta/violet/green -- passes CVD separation and
# the normal-vision floor for a 6-series all-pairs-adjacent scenario, with a
# contrast WARN that this script satisfies via direct labels (see module
# docstring). Assigned in TARGET_REGIONS' fixed dict order -- never re-cycled
# per plot, so a region's color means the same thing on every month's chart.
REGION_COLORS = {
    'Europe': '#2a78d6',         # blue
    'Caribbean': '#eda100',      # yellow
    'South America': '#1baf7a',  # aqua
    'Africa': '#e87ba4',         # magenta
    'Asia': '#4a3aa7',           # violet
    'Oceania': '#008300',        # green
}

# TARGET_REGIONS' azimuth windows genuinely overlap at this site's
# latitude (Caribbean 120-180 / South America 150-210 share 150-180;
# Europe 30-90 / Africa 60-120 share 60-90) -- so several regions' best-day
# peaks routinely land within a few degrees of each other on the chart. A
# label nudged a fixed few pixels from ITS OWN point still collides with a
# neighboring region's point (and label) sitting right next to it.
#
# The fix: every region's label lives at a FIXED position in axes-fraction
# space (outside the circle, in its own quadrant), never at an offset from
# the point itself -- so two regions' labels can never collide with each
# other no matter how close their actual tracks land. A thin leader line
# (colored to match the track) connects each label back to that region's
# peak marker. Anchor quadrants are chosen to roughly match where each
# region's window sits (Europe/Africa to the right since their windows are
# NE-E-ESE; Caribbean/South America lower-right and lower-left since their
# windows are SE-S-SW; Oceania/Asia to the left since their windows are
# W-NW-N), so leader lines stay short and don't cross the plot.
REGION_LABEL_ANCHOR = {
    'Europe':        (1.18, 0.82, 'left'),
    'Africa':        (1.18, 0.50, 'left'),
    'Caribbean':     (1.18, 0.14, 'left'),
    'South America': (-0.18, 0.14, 'right'),
    'Oceania':       (-0.18, 0.50, 'right'),
    'Asia':          (-0.18, 0.82, 'right'),
}


def build_month_plot(month, year, region_infos, calc, terrain, offset_e, offset_n,
                      min_elev_deg, band_mhz, out_path, site_label):
    """region_infos: list of (region, monthly_conditions_info_dict) for
    every region that has a qualifying best day this month."""
    fig = plt.figure(figsize=(8, 8), dpi=150)
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_rlim(0, 90)
    ax.set_rlabel_position(200)
    ax.set_yticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_yticklabels(['90', '75', '60', '45', '30', '15', '0'], fontsize=7)
    ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], fontsize=9)
    ax.grid(color='#CCCCCC', linewidth=0.6)
    ax.set_facecolor('white')

    az_samples = np.linspace(0, 360, 361)
    horizon = np.array([
        terrain.horizon_angle_deg(a, offset_e, offset_n) if terrain else 0.0
        for a in az_samples
    ])
    theta_h = np.radians(az_samples)
    r_boundary = 90.0 - np.clip(horizon, 0, 90)
    ax.fill_between(theta_h, r_boundary, 90.0, where=(horizon > 0.01),
                     color=OBSTRUCTION_FILL, alpha=OBSTRUCTION_ALPHA,
                     linewidth=0, zorder=1)
    ax.plot(theta_h, r_boundary, color='#7A7A7A', linewidth=1.0, zorder=2)

    min_elev_r = 90.0 - min_elev_deg
    ax.plot(np.radians(az_samples), np.full_like(az_samples, min_elev_r),
            linestyle=':', color='#999999', linewidth=1.0, zorder=2)

    for region, info in region_infos:
        color = REGION_COLORS.get(region, '#555555')
        anchor_x, anchor_y, ha = REGION_LABEL_ANCHOR.get(region, (1.18, 0.5, 'left'))
        best_date = datetime.strptime(info['best_date'], '%Y-%m-%d')
        track = calc.get_pass_track_for_date(best_date, region, band_mhz)
        if not track:
            continue

        az = np.array([p['azimuth'] for p in track])
        el = np.array([p['elevation'] for p in track])
        theta = np.radians(az)
        r = 90.0 - el

        ax.plot(theta, r, color=color, linewidth=2.2, zorder=3, solid_capstyle='round')

        start, end = track[0], track[-1]
        peak_idx = int(np.argmax(el))
        peak = track[peak_idx]

        ax.scatter([np.radians(start['azimuth'])], [90.0 - start['elevation']],
                   marker='^', s=70, facecolors='white', edgecolors=color,
                   linewidths=1.6, zorder=4)
        ax.scatter([np.radians(end['azimuth'])], [90.0 - end['elevation']],
                   marker='v', s=70, facecolors='white', edgecolors=color,
                   linewidths=1.6, zorder=4)
        ax.scatter([np.radians(peak['azimuth'])], [90.0 - peak['elevation']],
                   marker='*', s=200, facecolors=color, edgecolors='black',
                   linewidths=0.8, zorder=5)

        # One fixed-position label per region (never offset from the point
        # itself -- see REGION_LABEL_ANCHOR comment above), with a thin
        # leader line back to the peak marker so it's unambiguous which
        # track it belongs to. This carries all three requested elevation
        # values (start/peak/end) plus the region name, without letting
        # two regions' text collide even when their tracks sit right next
        # to each other.
        ax.annotate('', xy=(np.radians(peak['azimuth']), 90.0 - peak['elevation']),
                    xycoords='data', xytext=(anchor_x, anchor_y), textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='-', color=color, linewidth=0.9,
                                     shrinkA=2, shrinkB=6,
                                     connectionstyle='arc3,rad=0.15'),
                    zorder=6, annotation_clip=False)
        ax.text(anchor_x, anchor_y, region, transform=ax.transAxes,
                 color=color, fontweight='bold', fontsize=8.5,
                 ha=ha, va='bottom', clip_on=False, zorder=7)
        ax.text(anchor_x, anchor_y - 0.028,
                 f"start {start['elevation']:.1f}°  ·  peak {peak['elevation']:.1f}°  ·  "
                 f"end {end['elevation']:.1f}°",
                 transform=ax.transAxes, color='#2b2b2b', fontsize=7,
                 ha=ha, va='top', clip_on=False, zorder=7,
                 bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=2))

    n_regions = len(region_infos)
    ax.set_title(
        f"Best EME pass by region — {MONTH_NAMES[month-1]} {year}\n"
        f"{site_label}, {band_mhz} MHz — {n_regions} region(s) with a qualifying pass",
        fontsize=11, pad=20
    )

    shape_handles = [
        plt.Line2D([0], [0], marker='^', color='none', markeredgecolor='#444444',
                   markerfacecolor='white', markersize=9, linestyle='none',
                   label='Pass start'),
        plt.Line2D([0], [0], marker='*', color='none', markerfacecolor='#444444',
                   markeredgecolor='black', markersize=13, linestyle='none',
                   label='Peak (lowest degradation)'),
        plt.Line2D([0], [0], marker='v', color='none', markeredgecolor='#444444',
                   markerfacecolor='white', markersize=9, linestyle='none',
                   label='Pass end'),
        plt.Line2D([0], [0], color='#7A7A7A', lw=1.5, label='Local obstruction horizon'),
        plt.Line2D([0], [0], color='#999999', lw=1.2, linestyle=':',
                   label=f'{band_mhz} MHz min elevation ({min_elev_deg:.0f}°)'),
    ]
    region_handles = [
        plt.Line2D([0], [0], color=REGION_COLORS.get(region, '#555555'), lw=2.2,
                   label=f"{region} — {info['best_date']} ({info['degradation_db']:.2f} dB)")
        for region, info in region_infos
    ]
    # Figure-level legends (not axes-level): the side labels already push
    # the "tight" bounding box well past the axes edges, so anchoring to
    # axes fraction here (as the annual scatter plots do) made the two
    # legend blocks collide. Figure-fraction anchoring plus an explicit
    # bottom margin keeps them predictably stacked below everything else
    # regardless of how far the side labels extend.
    fig.subplots_adjust(bottom=0.24, left=0.02, right=0.98, top=0.88)
    fig.legend(handles=shape_handles, loc='lower center', bbox_to_anchor=(0.5, 0.10),
               fontsize=7.5, frameon=False, ncol=5)
    fig.legend(handles=region_handles, loc='lower center', bbox_to_anchor=(0.5, 0.0),
               fontsize=7.5, frameon=False, ncol=3, title='Region — best date (degradation)',
               title_fontsize=7.5)

    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--band', type=int, default=1296)
    ap.add_argument('--offset-east-ft', type=float, default=0.0)
    ap.add_argument('--offset-north-ft', type=float, default=0.0)
    ap.add_argument('--days', type=int, default=365)
    ap.add_argument('--start-date', help='YYYY-MM-DD, default: 1st of the current month')
    ap.add_argument('--out-dir', default='docs/plots/monthly_tracks')
    ap.add_argument('--noise-figure-db', type=float, default=None,
                     help="Receiver noise figure in dB at the antenna feedpoint. "
                          "Overrides the profile's receiver_noise_figure_db map and "
                          "the built-in generic defaults.")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    terrain = TerrainProfile(args.profile)
    calc = EMECalculator(terrain_profile=terrain,
                          offset_east_ft=args.offset_east_ft,
                          offset_north_ft=args.offset_north_ft)
    calc.setup_observer(terrain.latitude, terrain.longitude, terrain.elevation_ft * 0.3048)

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    daily_passes = calc.calculate_daily_passes(start_date, frequency_mhz=args.band, days=args.days)
    opportunities = calc.analyze_eme_opportunities(
        daily_passes, frequency_mhz=args.band, noise_figure_db=args.noise_figure_db
    )
    monthly = calc.monthly_conditions(opportunities)

    min_elev_deg = calc.min_elevation_for_band(args.band)
    noise_figure_db = calc.noise_figure_db_for_band(args.band, args.noise_figure_db)
    site_label = terrain.profile.get('profile_name', terrain.profile.get('grid_square', 'site'))

    print(f"Rx noise figure: {noise_figure_db:.2f} dB")

    for month in range(1, 13):
        region_infos = [
            (region, monthly[region][month])
            for region in EMECalculator.TARGET_REGIONS
            if monthly.get(region, {}).get(month)
        ]
        if not region_infos:
            print(f"{MONTH_NAMES[month-1]}: no region has a qualifying pass -- skipped")
            continue
        # Use the year of whichever best_date happens to be earliest, for a
        # stable, sensible title even if regions' best days span a year edge.
        year = min(datetime.strptime(info['best_date'], '%Y-%m-%d').year
                    for _, info in region_infos)
        out_path = os.path.join(args.out_dir, f"{month:02d}_{MONTH_NAMES[month-1].lower()}.png")
        build_month_plot(month, year, region_infos, calc, terrain,
                          args.offset_east_ft, args.offset_north_ft,
                          min_elev_deg, args.band, out_path, site_label)
        print(f"Wrote {out_path} ({len(region_infos)} region(s))")


if __name__ == '__main__':
    main()
