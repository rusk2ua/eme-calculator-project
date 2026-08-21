# EME Dish Siting Calculator

A tool for amateur radio operators to answer two questions, in order: **where on my property should I put an EME antenna** — given the specific trees, terrain, and obstructions that actually surround it — and **once it's there, at exactly which azimuth and elevation is the Moon actually usable**, band by band, month by month, night by night.

## Overview

Siting is the primary job. Everything else in this tool exists to support it: you describe your property's real obstructions (tree lines, tree clusters, regional terrain) in a **site profile**, and the calculator turns that into the actual usable azimuth/elevation windows for each target region — not a theoretical flat-horizon estimate, but what your Moon passes really look like once your trees and terrain are accounted for. See the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md) for the full walkthrough and a worked example.

Once a site is modeled, the calculator also analyzes:

- Moon position calculations throughout the year (via PyEphem)
- Optimal azimuth ranges for target regions, gated by band-specific minimum elevation
- EME degradation (sky noise + lunar distance) to rank each month's best pass, not just the highest one
- Wind loading considerations
- Frequency-specific RF considerations

## Features

- **Site Profile Modeling**: direction-aware tree lines, tree clusters, and a USGS-elevation-derived regional terrain floor, all described in one JSON file per property — see the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md)
- **Location Input**: a full site profile (JSON, recommended), or a quicker Maidenhead grid square / lat-lon estimate without one
- **Multi-band Support**: 144 MHz, 432 MHz, 902 MHz, 1296 MHz, 2304 MHz, 3456 MHz, 5760 MHz, 10 GHz+
- **Target Regions**: Europe, Caribbean, South America, Africa, Asia, Oceania
- **Band-Specific Minimum Elevation**: pass counting uses each band's real minimum usable elevation instead of one hardcoded value for every band
- **"What if I moved the dish" Re-runs**: re-analyze the same site with the antenna offset a given distance east/north, without re-surveying obstructions
- **Polar Az/El Plots, Monthly Best-Day Track Plots & Monthly Tables**: visualize exactly which azimuth/elevation combinations are usable — see the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md) for a full worked example
- **Operating Schedule**: Moonrise-to-moonset operating windows
- **Web Interface**: Easy-to-use calculator with visual results
- **Serverless Deployment**: AWS Lambda-based backend

> **Note:** the Lambda/web interface (`lambda/`, `web/`) currently implements the original single-direction tree model. The direction-aware `TerrainProfile` / site-profile workflow described below is CLI-only (`src/eme_calculator.py`) as of this revision — wiring it into the Lambda handler is tracked as a follow-up, not yet done.

## Quick Start

### Web Interface
Visit the deployed calculator at: `https://your-api-gateway-url.amazonaws.com`

### Local Development
Use a virtual environment so the project's dependencies stay isolated from your system Python:
```bash
git clone https://github.com/rusk2ua/eme-dish-calculator.git
cd eme-dish-calculator

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
python src/eme_calculator.py --grid FN12fr46 --band 1296
```
The venv only needs creating once. Next time, just `cd` into the project and run `source venv/bin/activate` (or `venv\Scripts\activate` on Windows) again — the dependencies are already installed. Run `deactivate` when you're done. See [Virtual Environment Setup](#virtual-environment-setup) below for more detail, including why `venv/` and `.aws-sam/` never get committed.

Running that last command in a real terminal prints a short human-readable summary (annual pass counts, wind loading, RF notes) — that's the calculator running an analysis and reporting back, not a bug. See [Reading the CLI output](#reading-the-cli-output) below for the other output modes.

### Analyzing a real site with a directional obstruction profile
```bash
python src/eme_calculator.py \
  --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --band 1296 --dish-diameter 2.4 --wind-speed 35 \
  --start-date 2026-01-01 --days 365
```
This prints the same kind of summary as above, computed from the real obstruction-modeled site instead of a flat-horizon grid square, plus an EME degradation figure (sky noise + Moon distance, see [Methodology & Limitations](#methodology--limitations)) computed using the site profile's `receiver_noise_figure_db` values -- override with `--noise-figure-db <dB>` if you want to try a different preamp than the one in the profile. For the full monthly-by-region breakdown and the plots, use `scripts/generate_polar_plots.py` (see the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md) for a worked example) rather than trying to read it out of this command's output.

### Reading the CLI output

`src/eme_calculator.py` has three output modes:

| You run it... | You get |
|---|---|
| Plainly, in a terminal (no `--output`/`--json`) | A short human-readable summary: pass counts per region, wind loading, RF notes |
| With `--output results.json` | The summary printed to the terminal **and** the full results (including the monthly-by-region breakdown) saved as JSON to that file |
| With `--json`, or piped/redirected (e.g. `... \| jq .`, `... > results.json`) | The full results as JSON on stdout, no summary |

The full JSON is what `scripts/generate_polar_plots.py` consumes internally to build the plots and `docs/monthly_conditions.md` — you don't need to read it by hand unless you're scripting against it.

Any `--output some_file.json` you save directly in the project root is gitignored (`/*.json` in `.gitignore`, anchored to the root only so it doesn't touch tracked JSON like the site profiles or the sky-noise grid) — safe to leave lying around for your own reference without it turning up in `git status`.

## Site Profile: Modeling Your Own Property

The site profile JSON is how you tell the calculator what's actually blocking your view of the sky, in every direction, from your own patch of ground — see [Features](#features) above for why that's the primary thing this tool does.

Two things about the output are easy to misread if you haven't seen them explained, so they're worth flagging here even though the full explanation lives in the guide:

- **The gray wedge on every polar plot is your obstruction horizon** — a direct picture of the tree lines, tree clusters, and regional terrain floor in your site profile, not a rendering artifact or a fixed decoration.
- **Not every azimuth ever gets a moonrise or moonset, regardless of obstructions** — at any given latitude, the Moon's rise/set azimuth is geometrically bounded (it swings roughly ±18° to ±29° in declination over an 18.6-year cycle), so a real sector of the compass can be permanently below the horizon there no matter how clear the trees are.

**[Read the full Site Profile Guide →](docs/SITE_PROFILE_GUIDE.md)** — the JSON schema field by field, both of the points above explained in detail, and a complete worked example (K2UA station, grid square FN12fr46wo): the obstruction survey, corrected pass counts, all the polar and monthly-track plots, wind loading/RF numbers, EME degradation and receiver noise figure, and "what if I moved the dish" scenarios.

![Monthly best-day pass tracks — January, K2UA FN12fr46wo](docs/plots/monthly_tracks/01_january.png)
*One example from the worked example's monthly best-day pass track plots — see the guide for the full set and what everything on it means.*

## Installation & Deployment

### Local Setup
```bash
# Clone repository
git clone https://github.com/rusk2ua/eme-dish-calculator.git
cd eme-dish-calculator

# Create and activate a virtual environment (see Virtual Environment Setup below)
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install dependencies into the venv
pip install -r requirements.txt

# Run calculations
python src/eme_calculator.py --help
```

### Virtual Environment Setup

`requirements.txt` installs into whatever Python `pip` currently points at. Without a virtual environment, that's your system (or Homebrew) Python — fine until a second project needs a different version of the same package, or you want to blow everything away and start clean without touching anything else on the machine. A venv sidesteps that: it's a self-contained copy of Python plus whatever gets `pip install`ed into it, isolated from everything else.

```bash
# One-time setup, from the project root
python3 -m venv venv

# Every time you start working (new terminal, new session)
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt   # only needed again if requirements.txt changed

# ... do your work: python src/eme_calculator.py ..., python -m pytest tests/, etc ...

# When done
deactivate
```

A `(venv)` prefix on your shell prompt means it's active. `venv/` is already in `.gitignore` — it's a local build artifact, never committed, and safe to delete and recreate (`rm -rf venv && python3 -m venv venv`) any time it gets into a weird state.

**Note on `aws-sam-cli`**: install this one globally (`pip install aws-sam-cli` outside any venv, or `brew install aws-sam-cli` on macOS) rather than inside this project's venv. It's a general-purpose CLI you'll want on your `PATH` across every AWS project, not a dependency of this one — installing it into a per-project venv means `sam` only works while that venv happens to be active, which gets confusing fast.

### AWS Deployment
```bash
# Build and deploy (sam CLI installed globally -- see note above)
sam build
sam deploy --guided
```

## API Usage

### Calculate EME Windows
```bash
curl -X POST https://your-api.amazonaws.com/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "grid_square": "FN12fr46",
    "frequency_mhz": 1296,
    "dish_diameter_m": 2.4,
    "tree_height_ft": 80,
    "tree_distance_ft": 100,
    "max_wind_mph": 50,
    "target_regions": ["Europe", "Caribbean"]
  }'
```

### Response Format
```json
{
  "location": {
    "grid_square": "FN12fr46",
    "latitude": 42.733333,
    "longitude": -77.550000,
    "elevation_m": 500
  },
  "recommendations": {
    "optimal_location": "150-200 feet east of house",
    "azimuth_range": "30°-210°",
    "foundation_requirements": "Reinforced concrete for 400+ lbf"
  },
  "eme_windows": {
    "Europe": {
      "annual_passes": 132,
      "avg_hours_after_moonrise": 2.7
    }
  },
  "rf_considerations": {
    "frequency_mhz": 1296,
    "wavelength_cm": 23.1,
    "tree_loss_db": 15.2,
    "rain_fade_db": 2.1
  }
}
```
> This response shape is illustrative of the web/Lambda API, which (see the note under Features) has not yet been updated to the corrected pass-counting/terrain model — the CLI is authoritative as of this revision.

## Frequency Band Considerations

| Band | Frequency | Wavelength | Tree Sensitivity | Rain Fade |
|------|-----------|------------|------------------|-----------|
| 2m   | 144 MHz   | 208 cm     | Low              | Minimal   |
| 70cm | 432 MHz   | 69 cm      | Medium           | Low       |
| 33cm | 902 MHz   | 33 cm      | Medium           | Medium    |
| 23cm | 1296 MHz  | 23 cm      | High             | Medium    |
| 13cm | 2304 MHz  | 13 cm      | Very High        | High      |
| 9cm  | 3456 MHz  | 9 cm       | Extreme          | High      |
| 6cm  | 5760 MHz  | 5 cm       | Extreme          | Very High |
| 3cm  | 10 GHz    | 3 cm       | Extreme          | Very High |

## Methodology & Limitations

**Pass counting.** For every day in the analysis window, the Moon's track from moonrise to moonset is sampled every 10 minutes. A sample counts as "usable" for a region if its azimuth falls in that region's window AND its elevation clears both the band's minimum usable elevation (`RFAnalyzer.BAND_CHARACTERISTICS[band]['min_elevation_deg']`) and the local obstruction horizon at that azimuth. Each day contributes at most one pass per region — the highest-elevation usable sample that day.

**Two different "az/el range" figures, not one** (as of v2.2.0): `pass_azimuth_sweep_deg`/`pass_elevation_sweep_deg` is the min/max across every usable sample on the best day specifically — how far the Moon actually moves while it's inside a region's window that day, typically tens of degrees. `peak_azimuth_spread_deg`/`peak_elevation_spread_deg` is a different, much narrower thing: the min/max of just the single peak-elevation instant, one point per qualifying day, across every qualifying day in the month — how much that one moment drifts night to night, not how far any single pass sweeps. An earlier version reported only the day-to-day figure under the ambiguous name "azimuth range," which reads as the in-pass sweep and is off by an order of magnitude from it.

**Terrain/obstruction horizon** (`src/terrain.py`) combines two things: (1) explicit near-field features — tree lines modeled as finite line segments and tree clusters modeled as azimuth arcs, both with a 3° edge taper — and (2) a coarse regional "terrain floor" from 9 USGS National Map Elevation Point Query Service (EPQS) samples (site center + 8 compass octants at 2000ft range), piecewise-linearly interpolated by azimuth. The near-field features generally dominate wherever they're present, since a public DEM's 2000ft sample spacing cannot resolve individual tree lines. See the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md) for the JSON schema, how this becomes the gray wedge on the polar plots, and a full worked example.

**What this is not**: a dense ray-marched horizon profile. A proper one would sample terrain every few meters out to 20-30km on every azimuth. That wasn't feasible from this development environment's network sandbox (only a handful of allowlisted domains are reachable; general internet and the usual DEM tile/API hosts are not) — `fetch_octant_samples()` and `fetch_elevation_ft()` in `terrain.py` are real, working USGS EPQS client code that will run at full resolution wherever this is executed with normal internet access. If you want denser coverage, swap in [py3dep](https://github.com/hyriver/py3dep) (USGS 3DEP, 1-10m resolution over the US), `elevation`/`srtm.py` (SRTM 30-90m, global), or [AWS Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) (public S3, Terrarium-encoded PNG DEM) — see the module docstring.

**EME degradation model** (`src/sky_noise.py`) ranks each month's "best day" by lowest degradation instead of highest elevation, as of v2.1.0. It combines two terms into one dB figure, 0 = best achievable for the selected band/receiver:

- **Sky (galactic) noise**: the diffuse galactic radio background varies hugely with where in the sky the Moon is (cold off the galactic plane, much hotter toward the galactic center/Cygnus X) and falls off steeply with frequency (dominant at 144MHz, down to a few K above the cosmic microwave background by 1296MHz and up). A real pixel-accurate map means the `pygdsm` package — healpy, h5py, astropy, scipy, plus a ~500MB one-time data download — which was evaluated and declined as disproportionate to this project's footprint. Instead, `data/sky_noise/galactic_408mhz_grid.json` is a **synthesized analytic approximation** on a coarse 15°×15° galactic-coordinate grid, calibrated to published landmark magnitudes (Haslam et al. 1982; off-plane floor ≈15-20K, galactic-plane general enhancement to the ~100-200K range, inner-galaxy enhancement to the low thousands of K within a 15° beam-averaged cell) — **not digitized survey pixels**. Frequency scaling uses ITU-R P.372-12 eq (15): `Tb(f) = Tb(408MHz)*(f/408)^-2.75 + 2.7K`. Swapping in `pygdsm` or real digitized survey values later is a drop-in upgrade to that one file; nothing else would need to change. Full derivation and citations are in the `src/sky_noise.py` module docstring.
- **Lunar distance (range factor)**: two-way (round-trip, R⁴) free-space path loss relative to a fixed perigee reference (356,500 km), which works out to ≈2.3 dB max at apogee — computed from `ephem`'s actual Moon-Earth distance for each sample, not a lookup table.
- **Receiver noise figure**: from the site profile's `receiver_noise_figure_db` (per-band, at the antenna feedpoint) or `--noise-figure-db`, converted to noise temperature via the standard `Te = 290*(10^(NF_dB/10)-1)` relationship.

This model started from a methodology summary the user supplied (paraphrased from WSJT-X/EME community practice). Two things in that summary didn't hold up against the references above and are corrected here — both explained in detail in the `sky_noise.py` docstring: the formula's sign was backwards (degradation went negative for worse conditions, contradicting its own "0dB=best, higher=worse" description), and the quoted 12-14dB apogee-to-perigee range is actually the sky-noise term's typical swing (real at 144MHz) misattributed to the much smaller (~2.3dB) distance term.

**What the degradation model is not**: an atmospheric/rain-attenuation or elevation-dependent-loss model (those are handled separately by `rf_considerations`' rain-fade estimate and the terrain horizon cutoff), or pixel-accurate galactic noise mapping (see above). The K2UA example profile's receiver noise figures are the operator's real station values as of v2.1.1 — see [EME degradation and receiver noise figure](docs/SITE_PROFILE_GUIDE.md#eme-degradation-and-receiver-noise-figure) in the Site Profile Guide — but a band you add to a profile without supplying its own NF still falls back to the generic `DEFAULT_NOISE_FIGURE_DB_BY_BAND` placeholder table.

## Rerunning for Other Scenarios

Every number in the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md)'s worked example is reproducible from the CLI — no code changes needed for a new band, dish size, or antenna position:

```bash
# Different band, same site
python src/eme_calculator.py --profile data/site_profiles/k2ua_fn12fr46wo.json --band 432

# Move the antenna (feet east/north of the profile's surveyed location)
python src/eme_calculator.py --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --offset-east-ft 50 --offset-north-ft -20

# Regenerate the polar plots + monthly tables for a scenario
python scripts/generate_polar_plots.py --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --band 902 --offset-east-ft -100 --out-dir docs/plots_902_west100

# Regenerate the monthly best-day pass track plots for a scenario
python scripts/generate_monthly_track_plots.py --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --band 902 --offset-east-ft -100 --out-dir docs/plots_902_west100/monthly_tracks
```

To model your own property, copy `data/site_profiles/k2ua_fn12fr46wo.json` and edit the coordinates, `elevation_ft`, and the obstruction lists — see the [Site Profile Guide](docs/SITE_PROFILE_GUIDE.md) for a field-by-field walkthrough — or fall back to `--grid` + `--tree-height`/`--tree-distance` for a quick single-direction estimate without a full profile.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2025-10-29 | Initial commit: EME dish siting calculator with 902 MHz and 10 GHz support |
| 1.1.0 | 2025-10-29 | Documentation updated with K2UA callsign |
| 1.1.1 | 2025-10-29 | README revision |
| 1.2.0 | 2025-10-29 | Added support for 6, 8, and 10-digit Maidenhead grid squares |
| 1.2.1 | 2026-08-18 | README revision |
| 1.2.2 | 2026-08-18 | README revision |
| **2.0.0** | **2026-08-20** | **Major revision.** Fixed a bug where `analyze_eme_opportunities()` counted every hourly sample within a region's azimuth window as a separate "pass," instead of one pass per calendar day — this let annual pass counts exceed 365 (physically impossible, the Moon rises once/day), which is what produced the case study's impossible 752 Caribbean / 499 South America / 617 Africa passes/year. Added `src/terrain.py`: direction-aware obstruction modeling combining operator-surveyed tree lines/clusters with a USGS EPQS-derived regional terrain floor, plus antenna-offset support for "what if I moved the dish" re-runs. Unified the minimum-usable-elevation threshold between `eme_calculator.py` and `rf_analysis.py` (previously two different hardcoded values, 10° flat vs. band-specific 5°-30°). Replaced the fictional FN12fr46 case study with the real K2UA station (FN12fr46wo), a full obstruction survey, USGS-sourced elevation, and corrected pass counts. Added polar az/el plots (`scripts/generate_polar_plots.py`, `docs/plots/`) and monthly peak-condition az/el tables (`docs/monthly_conditions.md`). Added `--start-date` for reproducible analysis windows. Added this Methodology & Limitations section and this Revision History. |
| 2.0.1 | 2026-08-20 | Corrected the west hardwood treeline's modeled extent from a placeholder symmetric 300ft-each-way assumption to the operator's field estimate: an asymmetric row at least 800ft long, starting ~200ft north of the due-west line and running south. Added `along_line_start_ft`/`along_line_end_ft` support to `terrain.py` for asymmetric rows (kept `half_length_ft` working for symmetric ones, e.g. the east pine row). No region's annual pass count changed — see Methodology & Limitations. |
| 2.0.2 | 2026-08-20 | Documentation only: local setup instructions (README Quick Start/Local Setup, DEPLOYMENT.md, PROJECT_STRUCTURE.md) now create and activate a Python virtual environment before `pip install`, instead of installing onto the system/Homebrew Python. Added a "Virtual Environment Setup" section to README.md. |
| 2.0.3 | 2026-08-21 | `src/eme_calculator.py`'s CLI printed a large raw JSON dump to the terminal with no explanation of what it was, which read as broken rather than working as intended. Added `format_summary()` and made it the default terminal output (pass counts, wind loading, RF notes); the full JSON is now opt-in via `--json`, via `--output <file>` (which also still prints the summary), or automatically when stdout is piped/redirected rather than an interactive terminal. See [Reading the CLI Output](#reading-the-cli-output). |
| **2.1.0** | **2026-08-21** | **EME degradation model.** Added `src/sky_noise.py`: sky (galactic) noise + lunar-distance path loss combined into a single dB degradation figure per pass (0dB = best achievable for the band/receiver). `monthly_conditions()` now ranks each month's "best day" by lowest degradation instead of highest peak elevation. Added `receiver_noise_figure_db` (per-band, at the antenna feedpoint) to the site profile schema, with a `--noise-figure-db` CLI override and generic per-band fallback defaults; seeded the K2UA profile with placeholder values pending real measurements. Corrected two errors found in the user-supplied source methodology during research (see Methodology & Limitations): a backwards degradation sign, and a 12-14dB apogee-to-perigee range-factor figure that was actually sky-noise swing misattributed to the (~2.3dB) distance term. Sky noise uses a synthesized, dependency-free analytic approximation of the galactic 408MHz background (`data/sky_noise/galactic_408mhz_grid.json`) rather than the `pygdsm` package, after evaluating and declining its ~500MB data download and heavy dependency chain (healpy/h5py/astropy/scipy) as disproportionate to this project. Polar plots now star each month's best-degradation day; monthly tables gained a Degradation (dB) column. No new dependencies. |
| 2.1.1 | 2026-08-21 | Replaced the v2.1.0 placeholder receiver noise figures in the K2UA profile with the operator's real station values: 0.5dB at 144/432 MHz, 0.25dB at 1296 MHz, 0.4dB at 2304 MHz, 0.9dB at 10368 MHz. Fixed a display rounding issue where 0.25dB printed as "0.2 dB" (Python's `.1f` uses round-half-to-even); noise-figure display now uses two decimal places throughout. Regenerated the case study's plots, `docs/monthly_conditions.md`, and README excerpt with the real values — degradation figures shifted slightly (e.g. Caribbean's avg. degradation 1.5dB→1.7dB at 1296 MHz); no region's annual pass count or any month's best-date pick changed. |
| **2.2.0** | **2026-08-21** | **Split the ambiguous "azimuth/elevation range" into two correctly-named, independently-computed fields.** The old `month_azimuth_range_deg`/`month_elevation_range_deg` was only ever the day-to-day spread of each day's single peak-elevation instant (typically 5-8° of azimuth) — read naturally, that name implies the full moonrise-to-moonset sweep during one pass, which is routinely 100°+ and is a completely different number. `analyze_eme_opportunities()` now tracks the min/max azimuth and elevation across every usable sample on each day (not just the peak), so `monthly_conditions()` can report both: `pass_azimuth_sweep_deg`/`pass_elevation_sweep_deg` (how far the Moon moves during the best day's actual pass through the region window — tens of degrees) and `peak_azimuth_spread_deg`/`peak_elevation_spread_deg` (the renamed day-to-day figure, unchanged in meaning). `docs/monthly_conditions.md` and the README excerpt gained two columns accordingly. No pass counts, degradation values, or best-day picks changed — this is a reporting-detail addition and rename, not a recalculation. Also fixed a stale Methodology & Limitations sentence still describing the K2UA profile's noise figures as placeholders after v2.1.1 replaced them with real values. Added 1 new test (18 total, all passing). |
| 2.2.1 | 2026-08-21 | Added `/*.json` to `.gitignore`, anchored to the project root only (leading slash, no directory wildcard) so it catches stray `--output` result dumps left in the repo root without touching tracked JSON that belongs in the repo (`data/site_profiles/*.json`, `data/sky_noise/*.json`). Prompted by a real `--output` file accidentally getting swept into the v2.2.0 commit via `git add -A`, caught and removed before push. Documented in [Reading the CLI Output](#reading-the-cli-output). |
| **2.3.0** | **2026-08-21** | **Monthly best-day pass track plots.** Added `scripts/generate_monthly_track_plots.py` and `src/eme_calculator.py`'s new `get_pass_track_for_date()` (the ordered, time-sequenced counterpart to `pass_azimuth_sweep_deg`/`pass_elevation_sweep_deg` — the actual sample-by-sample path, not just its min/max). Produces one polar plot per calendar month, all six regions overlaid, showing only that month's single lowest-degradation day's real track as a connected line with the start (▲), peak (★), and end (▽) marked and elevation-labeled — a separate, additive view alongside the existing annual per-region scatter plots (`docs/plots/monthly_tracks/`, `docs/plots/` unchanged). Because several regions' azimuth windows genuinely overlap at this latitude (Caribbean/South America share 150°-180°, Europe/Africa share 60°-90°), their best-day peaks often land close together on the chart; rather than offsetting each label a fixed distance from its own point (which still collided when two regions' points sit next to each other), every region's name + start/peak/end elevation label lives at a fixed position around the outside of the circle with a thin leader line back to its track, so labels never collide regardless of how tightly the underlying tracks cluster. Palette (6-color categorical, validated with the project's dataviz-skill `validate_palette.js` under the strict "all pairs" mode) and marker shapes are shared with no color-alone identity. Added 2 new tests (20 total, all passing). No new dependencies (matplotlib/numpy already required). |
| **2.4.0** | **2026-08-21** | **Documentation restructure: separated "how the tool works" from "one operator's specific property."** README Overview/Features now lead with the project's actual primary goal — siting an antenna against real obstructions, then finding the usable az/el windows for that placement — instead of burying it under a long worked example. Moved the entire K2UA/FN12fr46wo case study (obstruction survey, corrected pass counts, all plots, wind loading/RF, EME degradation/NF, "what if" re-runs, and the west-treeline field-estimate revision narrative) out of README.md into a new [`docs/SITE_PROFILE_GUIDE.md`](docs/SITE_PROFILE_GUIDE.md), reframed as a general "how to build a site profile for your own property" guide with K2UA as its worked example, plus a field-by-field JSON schema reference. Added two explanations that were previously implicit or scattered: why the polar plots' gray wedge looks the way it does (a direct rendering of `horizon_angle_deg()`, not a fixed decoration), and why moonrise/moonset aren't available at every azimuth regardless of obstructions — a purely astronomical constraint from lunar declination range vs. site latitude, now backed by an actual `ephem` computation over a full 2020-2039 nodal cycle showing the Moon's azimuth (whenever above the horizon at K2UA's latitude) stays within roughly 49°-311°, leaving a permanent ~98°-wide blind sector (WNW through N to NE) that no amount of tree-clearing can open up — the real reason Asia's window returns ~0 passes. README's Methodology & Limitations section kept only the general, site-independent algorithm descriptions; site-specific field notes moved to the new guide. No code changes. |

## Acknowledgments

- PyEphem library for astronomical calculations
- USGS National Map Elevation Point Query Service for site and regional terrain elevation data
- Amateur radio EME community for operational insights
- AWS for serverless infrastructure

## Support

- Create an issue for bug reports or feature requests
- Join the discussion in the amateur radio EME forums

---

**73 de K2UA**
