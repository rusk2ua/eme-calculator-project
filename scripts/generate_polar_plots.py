#!/usr/bin/env python3
"""
Generate polar az/el "range of possible passes" plots and monthly
peak-conditions tables for each target region, for a given site profile
and band.

Usage:
    python3 scripts/generate_polar_plots.py \
        --profile data/site_profiles/k2ua_fn12fr46wo.json \
        --band 1296 --out-dir docs/plots

Each plot is a polar chart with elevation as the radius (90deg/zenith at
the center, 0deg/horizon at the rim) and azimuth as the angle (0=North
at top, clockwise). The shaded gray wedge is the local obstruction
horizon (terrain + trees) at each azimuth; the region's nominal azimuth
window is marked with dashed radial guides; every qualifying day's peak
(highest-elevation, least-degraded) Moon position is plotted as a dot,
colored by month with the perceptually-uniform 'viridis' colormap.
(A cyclic colormap like 'twilight' would be the technically purer choice
for month-of-year data, but twilight's endpoints are near-white and
several months' dots would nearly disappear against this plot's white
background -- viridis has no near-white step, so every month stays
legible, at the minor cost of Dec and Jan not being visually adjacent.)
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

MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

OBSTRUCTION_FILL = '#B0B0B0'
OBSTRUCTION_ALPHA = 0.55
GUIDE_COLOR = '#4A4A4A'


def build_region_plot(region, min_az, max_az, passes, terrain, offset_e, offset_n,
                       min_elev_deg, out_path, site_label, band_mhz):
    fig = plt.figure(figsize=(7.5, 7.5), dpi=150)
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)  # clockwise, matches compass convention
    ax.set_rlim(0, 90)
    ax.set_rlabel_position(200)
    ax.set_yticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_yticklabels(['90', '75', '60', '45', '30', '15', '0'], fontsize=7)
    ax.set_xticks(np.radians([0, 45, 90, 135, 180, 225, 270, 315]))
    ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], fontsize=9)
    ax.grid(color='#CCCCCC', linewidth=0.6)
    ax.set_facecolor('white')

    # Obstruction horizon wedge, sampled every 1 degree of azimuth. Radius
    # is measured from the center (zenith, r=0) outward to the rim
    # (horizon, r=90), so a filled-in obstruction runs from r=0 out to
    # r = 90 - horizon_angle.
    az_samples = np.linspace(0, 360, 361)
    horizon = np.array([
        terrain.horizon_angle_deg(a, offset_e, offset_n) if terrain else 0.0
        for a in az_samples
    ])
    theta = np.radians(az_samples)
    # r=0 is the zenith (90deg elevation), r=90 is the rim (0deg, the
    # horizon). An obstruction of `horizon` degrees blocks everything
    # from the rim inward to r = 90 - horizon -- i.e. the blocked band is
    # [90-horizon, 90], NOT [0, 90-horizon] (that would shade the clear
    # sky near the zenith instead of the blocked sky near the horizon).
    r_boundary = 90.0 - np.clip(horizon, 0, 90)
    ax.fill_between(theta, r_boundary, 90.0,
                     where=(horizon > 0.01),
                     color=OBSTRUCTION_FILL, alpha=OBSTRUCTION_ALPHA,
                     linewidth=0, zorder=1)
    ax.plot(theta, r_boundary, color='#7A7A7A', linewidth=1.0, zorder=2)

    # Band minimum-elevation reference circle.
    min_elev_r = 90.0 - min_elev_deg
    ax.plot(np.radians(az_samples), np.full_like(az_samples, min_elev_r),
            linestyle=':', color='#999999', linewidth=1.0, zorder=2,
            label=f'{band_mhz} MHz min elevation ({min_elev_deg:.0f} deg)')

    # Region azimuth window guides.
    for edge_az in (min_az, max_az):
        ax.plot([np.radians(edge_az), np.radians(edge_az)], [0, 90],
                linestyle='--', color=GUIDE_COLOR, linewidth=1.1, zorder=2)

    # Scatter every qualifying day's peak position, colored by month.
    if passes:
        months = np.array([p['date'].month for p in passes])
        az = np.array([p['azimuth'] for p in passes])
        el = np.array([p['elevation'] for p in passes])
        r = 90.0 - el
        sc = ax.scatter(np.radians(az), r, c=months, cmap='viridis',
                         vmin=1, vmax=12, s=14, alpha=0.85, zorder=3,
                         edgecolors='none')
        cbar = fig.colorbar(sc, ax=ax, pad=0.11, shrink=0.75, ticks=range(1, 13))
        cbar.ax.set_yticklabels(MONTH_ABBR, fontsize=7)
        cbar.set_label('Month of best (peak-elevation) pass', fontsize=8)

    n_passes = len(passes)
    ax.set_title(
        f"{region} -- range of possible EME passes\n"
        f"{site_label}, {band_mhz} MHz -- {n_passes} qualifying day(s)/yr "
        f"(azimuth window {min_az}-{max_az} deg)",
        fontsize=10, pad=18
    )

    handles = [
        plt.Line2D([0], [0], color='#7A7A7A', lw=1.5, label='Local obstruction horizon'),
        plt.Line2D([0], [0], color='#999999', lw=1.2, linestyle=':',
                   label=f'{band_mhz} MHz min elevation ({min_elev_deg:.0f} deg)'),
        plt.Line2D([0], [0], color=GUIDE_COLOR, lw=1.1, linestyle='--',
                   label='Region azimuth window'),
    ]
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.06),
              fontsize=7.5, frameon=False, ncol=1)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def format_monthly_table_md(region, monthly, min_elev_deg):
    lines = [
        f"### {region}",
        "",
        "| Month | Best date | Peak Az (deg) | Peak El (deg) | Az range (deg) | El range (deg) | Qualifying days |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in range(1, 13):
        info = monthly.get(m)
        if not info:
            lines.append(f"| {MONTH_ABBR[m-1]} | -- | -- | -- | -- | -- | 0 |")
            continue
        az_lo, az_hi = info['month_azimuth_range_deg']
        el_lo, el_hi = info['month_elevation_range_deg']
        lines.append(
            f"| {MONTH_ABBR[m-1]} | {info['best_date']} | "
            f"{info['peak_azimuth_deg']:.1f} | {info['peak_elevation_deg']:.1f} | "
            f"{az_lo:.1f}-{az_hi:.1f} | {el_lo:.1f}-{el_hi:.1f} | "
            f"{info['qualifying_days_in_month']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--band', type=int, default=1296)
    ap.add_argument('--dish-diameter', type=float, default=2.4)
    ap.add_argument('--offset-east-ft', type=float, default=0.0)
    ap.add_argument('--offset-north-ft', type=float, default=0.0)
    ap.add_argument('--days', type=int, default=365)
    ap.add_argument('--start-date', help='YYYY-MM-DD, default: 1st of the current month')
    ap.add_argument('--out-dir', default='docs/plots')
    ap.add_argument('--tables-out', default='docs/monthly_conditions.md')
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
    opportunities = calc.analyze_eme_opportunities(daily_passes)
    monthly = calc.monthly_conditions(opportunities)

    min_elev_deg = calc.min_elevation_for_band(args.band)
    site_label = terrain.profile.get('profile_name', terrain.profile.get('grid_square', 'site'))

    md_sections = [
        f"# Monthly Peak-Condition Az/El Tables\n",
        f"Site: {site_label} | Band: {args.band} MHz | "
        f"Antenna offset: {args.offset_east_ft:+.0f}ft E, {args.offset_north_ft:+.0f}ft N\n",
        "Each row is the SINGLE best (highest peak-elevation, i.e. least "
        "atmospheric-absorption and obstruction degradation) qualifying pass "
        "in that month, plus the azimuth/elevation range covered by every "
        "qualifying pass that month.\n",
    ]

    for region, (min_az, max_az) in EMECalculator.TARGET_REGIONS.items():
        passes = opportunities[region]
        out_path = os.path.join(args.out_dir, f"{region.lower().replace(' ', '_')}_polar.png")
        build_region_plot(region, min_az, max_az, passes, terrain,
                           args.offset_east_ft, args.offset_north_ft,
                           min_elev_deg, out_path, site_label, args.band)
        print(f"Wrote {out_path} ({len(passes)} qualifying days/yr)")
        md_sections.append(format_monthly_table_md(region, monthly[region], min_elev_deg))

    with open(args.tables_out, 'w') as f:
        f.write("\n".join(md_sections))
    print(f"Wrote {args.tables_out}")


if __name__ == '__main__':
    main()
