# Site Profile Guide: Siting Your EME Antenna

This tool exists to answer two questions, in order:

1. **Where on my property should I put an EME antenna** — given the specific trees, terrain, and other obstructions that actually surround it, not a generic flat-horizon assumption?
2. **Once it's there, at exactly which azimuth and elevation is the Moon actually usable** — band by band, month by month, night by night?

The **site profile** (a JSON file under `data/site_profiles/`) is how you answer question 1: it's the calculator's model of what's really blocking your view of the sky, in every direction, from your own patch of ground. Everything downstream — the pass counts, the polar plots, the monthly best-day tables — is question 2's answer, computed *from* that model. This guide covers how to build a site profile for your own property, how to read what the plots are showing you, and a complete worked example (K2UA's station, grid square FN12fr46wo) end to end.

## The site profile JSON, field by field

Top-level fields:

| Field | Meaning |
|---|---|
| `profile_name` | Free-text label, shown in plot titles |
| `grid_square` | Maidenhead locator (informational; `latitude`/`longitude` are what's actually used) |
| `latitude`, `longitude` | Decimal degrees, antenna's reference position |
| `elevation_ft` | Site elevation, feet ASL |
| `elevation_source` | Free-text provenance note (e.g. how you got `elevation_ft`) |
| `antenna_agl_ft` | Antenna height above ground level, feet (added to `elevation_ft` for line-of-sight geometry) |
| `notes` | Free-text — survey precision caveats, date, whatever's useful to a future you |
| `receiver_noise_figure_db` | Per-band noise figure (dB) at the antenna feedpoint — see [Rerunning for Other Scenarios](../README.md#rerunning-for-other-scenarios) in the main README |
| `dem_octant_samples_ft` | Coarse regional terrain floor — see below |
| `line_obstructions` | Tree lines / hedgerows / fences, modeled as finite line segments |
| `arc_obstructions` | Tree clusters / tall stands, modeled as a flat-topped azimuth arc |

**`line_obstructions`** — one entry per row of trees (or any linear obstruction). Each needs:

- `height_ft` — top of the obstruction above ground, feet
- `perp_distance_ft` — perpendicular distance from the antenna to the line, feet
- `bearing_deg` — compass bearing from the antenna to the *nearest point* on the line (the perpendicular-foot direction)
- `line_bearing_deg` — compass bearing the row itself runs along (e.g. `0` for a north-south row, `90` for east-west)
- Row extent along that line, **either**:
  - `half_length_ft` — for a row centered on the perpendicular-foot point, extending that far in both directions, **or**
  - `along_line_start_ft` / `along_line_end_ft` — for an asymmetric row, measured from the perpendicular-foot point in the `line_bearing_deg` direction (negative = the opposite direction). Use this whenever the row isn't actually centered on your antenna's due-line to it — which, in practice, is most real tree lines.

**`arc_obstructions`** — one entry per cluster/stand that's easier to describe as "tall trees somewhere in this azimuth range" than as a line:

- `az_start_deg`, `az_end_deg` — the azimuth span the cluster covers
- `distance_ft`, `height_ft` — a single representative distance and height for the whole span

Internally this becomes a flat-topped obstruction across that azimuth range, with a 3° linear taper at each edge so the horizon function doesn't jump discontinuously where a real tree cluster's silhouette actually thins out gradually (`terrain.py::_arc_feature_angle`).

**`dem_octant_samples_ft`** — a coarse regional "terrain floor," independent of your near-field surveyed obstructions: USGS elevation samples at 2000ft range on each of the 8 principal bearings (0°/45°/.../315°) from the antenna, plus `site_elevation_ft`. `TerrainProfile` piecewise-linearly interpolates between them by azimuth to fill in the gaps between (and sanity-check beyond) your explicit tree lines/clusters. Regenerate this block for a new site with `terrain.fetch_octant_samples(lat, lon)` (needs internet access to USGS EPQS — see the module docstring in `src/terrain.py` for denser alternatives like py3dep or SRTM if you want better-than-2000ft-spacing coverage).

**How these combine**: for any azimuth, `TerrainProfile.horizon_angle_deg()` evaluates every obstruction feature that covers that azimuth plus the DEM floor, and takes the **maximum** — whichever obstruction actually blocks the most sky at that azimuth wins, automatically. A closer, taller tree line always beats a farther DEM sample without you having to reason about which one "should" apply.

## How obstructions become the gray wedge on the polar plots

Every polar plot (`docs/plots/*.png`, `docs/plots/monthly_tracks/*.png`) draws elevation as the radius — zenith (90°) at the center, horizon (0°) at the rim — and azimuth as the angle, N at top, clockwise. For each azimuth sample around the circle, the plot calls `horizon_angle_deg()` and shades everything from that angle out to the rim: that's the gray wedge. It is a direct, literal picture of your `line_obstructions`/`arc_obstructions`/`dem_octant_samples_ft` — nothing more mysterious than "here's how much sky is blocked, in this direction, translated straight onto the chart." A pass track or scatter point that dips into the gray band would mean the Moon is behind your trees/terrain at that instant; the calculator never reports such a point as usable in the first place, so you should never actually see a marker inside the wedge — if you do, something in the profile doesn't match what's really out there.

The shape of the wedge is diagnostic. A deep, close-in bite in one direction means a close, tall obstruction dominates there (see the K2UA west edge below); a shallow, even shading around most of the circle means the DEM floor is doing most of the work because there's no close surveyed feature in that direction. If a wedge looks wrong for your property, it's almost always because a `bearing_deg`/`line_bearing_deg` pair is swapped or a `perp_distance_ft` is off — regenerate the plots after every profile edit and eyeball the wedge before trusting the pass counts.

## Why moonrise and moonset aren't available at every azimuth

This is a **separate constraint from terrain** — it would be true even standing in a perfectly flat, treeless field. At any fixed latitude, the range of azimuths where the Moon can rise or set is bounded by how far its declination swings, and the Moon's declination swings noticeably more than the Sun's: on top of Earth's ~23.4° axial tilt, the Moon's orbit is inclined a further ~5.1° to the ecliptic, and that extra tilt itself precesses through a ~18.6-year cycle (the "lunar standstill" cycle) — so the Moon's declination ranges roughly ±18.3° at "minor standstill" out to roughly ±28.6° at "major standstill," rather than the Sun's fixed ±23.4°.

Declination and observer latitude together fix the possible rise/set azimuths (same spherical geometry that bounds sunrise/sunset azimuth at your latitude, just with a wider swing). At K2UA's latitude (42.7°N), stepping through a full 2020–2039 nodal cycle with `ephem` shows the Moon's azimuth, whenever it's above the horizon at all, staying within roughly **49° to 311°** — moonrise lands somewhere between about 49° and 131° (NE-ish to SE-ish), moonset somewhere between about 229° and 311° (SW-ish to WNW-ish). The remaining ~98°-wide sector, roughly WNW through N to NE, is a **permanent blind zone**: at this latitude, over an entire lunar nodal cycle, the Moon is never above the horizon there at all, obstruction or no obstruction. That's the real reason the Asia region window (300°-360°, i.e. WNW-through-N) comes back with essentially zero qualifying passes in the case study below — not trees, geometry. You can reproduce this bound for your own latitude with a short `ephem` loop over `next_rising()`/`next_setting()` across a ~19-year span; there's no shortcut formula this project hardcodes, since it depends on your specific latitude.

Practically: before spending survey time on obstructions in a particular direction, check whether the Moon can ever reach that direction from your latitude at all — the sample calculation above is a fine template. `TARGET_REGIONS` in `src/eme_calculator.py` defines each region's azimuth window; if a region's window falls entirely inside your latitude's blind zone, no amount of tree-clearing will ever open it up.

## Worked example: K2UA station, FN12fr46wo

**Location**: FN12fr46wo (42.735913°N, 77.54235°W, 479.7m / 1573.9ft ASL, from USGS EPQS)
**Band**: 1296 MHz (23cm), min. usable elevation 10°
**Dish**: 2.4m parabolic, 35mph design wind / 50mph gust rating

### The obstruction survey behind this profile

| Feature | Height | Distance | Bearing | Notes |
|---|---|---|---|---|
| West hardwood treeline | 80 ft | 120 ft | 270° (due W), N-S row | At least 800ft long; begins ~200ft north of the due-west line and runs south from there |
| East pine row | 45 ft | 200 ft | 90° (due E), ~355°-175° tilt | ~350ft long, centered on the antenna's latitude |
| SE tall pine cluster | ≥70 ft | 150 ft | 120°-140° | |
| S tall pine cluster | ≥70 ft | 100 ft | 180°-195° | |
| Far south ridge + hardwoods | 75 ft canopy + measured terrain rise | 500 ft | 150°-210° (South America window) | Overridden by the closer SE/S clusters where they overlap |

Full machine-readable profile: [`data/site_profiles/k2ua_fn12fr46wo.json`](../data/site_profiles/k2ua_fn12fr46wo.json).

**Field-estimate precision**: heights and distances above are the operator's field estimates (±10ft on distance, ±5ft on height per the profile's own `notes`), not a survey-grade measurement. `calculate_tree_blockage()` and the single-direction `calculate_rf_considerations()` tree-loss estimate in `eme_calculator.py` are retained for backward compatibility but only model one direction each — prefer a full `TerrainProfile` (as this profile is) for anything direction-dependent, which in EME siting is essentially everything.

**How the west treeline's extent was pinned down** (a real example of iterating on a profile as better field data comes in): it was first modeled as an assumed 300ft-each-way symmetric row — an unmeasured placeholder, since all that was known initially was "trees, west, about 80ft tall, 120ft away." Once the operator supplied a field estimate — an asymmetric run at least 800ft long, starting ~200ft north of the due-west line and extending south from there — the profile switched from a symmetric `half_length_ft` to explicit `along_line_start_ft: -600` / `along_line_end_ft: 200`. That reshaped the obstruction wedge along the west/southwest edge of the polar plots (compare against an older render if you have one) but didn't flip any day's pass/no-pass outcome for the six regions this case study tracks — the azimuths where the two models disagree (150°-200° and 300°-330°) aren't where any region's daily peak sample lands. The row may run further south than the confirmed 800ft; if so, obstruction is understated for the southernmost few degrees of its span — `along_line_start_ft` is the field to extend if a longer confirmed length turns up. This is the general pattern for refining any profile: start from a conservative placeholder, replace it with field measurements as they come in, regenerate the plots, and check whether the wedge shape change actually moves any pass count before treating it as urgent.

### Corrected annual pass counts (2026 calendar year, 1296 MHz)

| Region | Azimuth window | Annual passes | Avg. peak elevation |
|---|---|---|---|
| Europe | 30°-90° | 132 | 30.9° |
| Caribbean | 120°-180° | 365 | 45.5° |
| South America | 150°-210° | 365 | 45.5° |
| Africa | 60°-120° | 222 | 43.2° |
| Asia | 300°-360° | 0 | — |
| Oceania | 240°-300° | 162 | 51.4° |

A "pass" is one calendar day at most, per region. Caribbean/South America land at 365 because at 42.7°N the Moon's daily culmination (its highest point of the day) sits roughly due south nearly every day of the year, comfortably clearing both the 10° band minimum and the local obstruction horizon in that direction almost every night it's up. Asia (300°-360°, roughly WNW-N) sits almost entirely inside this latitude's permanent moonrise/moonset blind zone described above — that's a geometry problem, not a tree problem; see [Why moonrise and moonset aren't available at every azimuth](#why-moonrise-and-moonset-arent-available-at-every-azimuth).

### Polar az/el plots — range of possible passes

Elevation is the radius (zenith at center, horizon at the rim); azimuth is the angle (N at top, clockwise). The gray band is the local obstruction horizon (see [above](#how-obstructions-become-the-gray-wedge-on-the-polar-plots)) — note how it bites in deepest along the west edge, where the close (120ft) 80ft hardwoods dominate, versus the shallower, more even shading elsewhere where the coarse DEM floor is doing most of the work. Dots are every qualifying day's peak-elevation Moon position, colored by month. The black-outlined star in each region is that month's single **best** day — lowest EME degradation (sky noise + Moon distance) — the same day listed in that region's row of the monthly table below.

| | |
|---|---|
| ![Europe](plots/europe_polar.png) | ![Caribbean](plots/caribbean_polar.png) |
| ![South America](plots/south_america_polar.png) | ![Africa](plots/africa_polar.png) |
| ![Oceania](plots/oceania_polar.png) | ![Asia](plots/asia_polar.png) |

Regenerate these with:
```bash
python scripts/generate_polar_plots.py \
  --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --band 1296 --start-date 2026-01-01 --days 365 \
  --out-dir docs/plots --tables-out docs/monthly_conditions.md
```

### Monthly best-day pass track plots — what the single best pass actually looks like

The plots above answer "what's the overall shape of the year for one region"; these answer "what does the single best pass actually look like, in real time." One chart per calendar month, every region overlaid, showing **only** that month's single lowest-degradation day's actual track — the real, connected az/el path the Moon travels from the moment it enters that region's window to the moment it leaves, not a scatter of many days. A star marks the peak (lowest-degradation) point; triangles mark the start (▲) and end (▽) of the track. Because several regions' windows genuinely overlap at this latitude (e.g. Caribbean/South America share 150°-180°) their best-day peaks often land close together on the chart, so each region's name + start/peak/end elevation labels live at a fixed position around the outside of the circle with a thin leader line back to its track, rather than floating next to the point itself — that keeps every label readable no matter how tightly the tracks cluster. January is shown below as an example:

![Monthly best-day pass tracks — January](plots/monthly_tracks/01_january.png)

The full set of 12 (one per month) is in [`docs/plots/monthly_tracks/`](plots/monthly_tracks). Regenerate with:
```bash
python scripts/generate_monthly_track_plots.py \
  --profile data/site_profiles/k2ua_fn12fr46wo.json \
  --band 1296 --start-date 2026-01-01 --days 365 \
  --out-dir docs/plots/monthly_tracks
```
This is a separate, additive script from `generate_polar_plots.py` above — it doesn't touch or replace the annual per-region scatter plots or `docs/monthly_conditions.md`.

### Monthly peak-condition az/el tables

Full tables for all six regions: [`monthly_conditions.md`](monthly_conditions.md). Each row is the single best (**lowest EME degradation** — sky noise + Moon distance, not simply highest elevation) qualifying pass that month. Two different az/el ranges are reported — see the note below the table — Caribbean excerpt (23cm, 0.25dB noise figure):

| Month | Best date | Degradation (dB) | Peak Az | Peak El | Pass Az sweep | Pass El sweep | Peak Az day-to-day spread | Peak El day-to-day spread | Qualifying days |
|---|---|---|---|---|---|---|---|---|---|
| Jan | 2026-01-03 | 0.14 | 176.5° | 71.5° | 122.7°-176.5° | 62.2°-71.5° | 172.5°-180.0° | 18.2°-75.2° | 31 |
| Jun | 2026-06-12 | 0.00 | 177.6° | 68.1° | 122.0°-177.6° | 56.3°-68.1° | 172.6°-179.8° | 18.5°-74.7° | 30 |
| Dec | 2026-12-25 | 0.00 | 178.2° | 66.8° | 122.8°-178.2° | 56.1°-66.8° | 172.9°-179.7° | 18.8°-74.5° | 31 |

**Pass Az/El sweep** is how far the Moon actually moves *during that one best day's pass* through this region's window — real tens-of-degrees movement, as you'd expect from rise to peak to set. **Peak Az/El day-to-day spread** is a different thing: how much just the peak *instant* (one point per day) drifts from one qualifying day to the next across the whole month — necessarily much narrower, since a region's peak tends to land at a similar azimuth night after night. See `Methodology & Limitations` in the main README for the general definition of both fields.

### Wind loading and RF

- **Wind loading**: 152.5 lbf @ 35mph design wind, 311.2 lbf @ 50mph gusts
- **23cm antenna gain / beamwidth** (2.4m dish, 60% efficiency): 28.1 dBi / 6.7°
- **Worst-case vegetation loss**: looking through the west hardwood treeline at low elevation (80ft trees, 120ft away) costs up to 40 dB (the model's cap) at 1296 MHz — exactly why the terrain-aware pass count excludes that azimuth/elevation combination rather than trying to estimate a loss for it

### EME degradation and receiver noise figure

Every qualifying pass carries an EME degradation figure in dB — 0 dB is the best achievable sky-noise + Moon-distance conditions for the selected band and receiver, higher is worse — computed from where the Moon sits relative to the galactic plane/center that day and how close it is to perigee. This is what drives the "best date" pick in the tables and the star markers on the plots above; see `Methodology & Limitations` in the main README for the model and its sourcing.

It depends on the receiver's noise figure (NF, dB, at the antenna feedpoint), which this profile sets from the operator's actual station values — 0.5dB at 144/432, 0.25dB at 1296, 0.4dB at 2304, 0.9dB at 10368 (see `receiver_noise_figure_db` in [`k2ua_fn12fr46wo.json`](../data/site_profiles/k2ua_fn12fr46wo.json)). Bands not in that list (902, 3456, 5760) fall back to the generic `DEFAULT_NOISE_FIGURE_DB_BY_BAND` placeholder table in `eme_calculator.py`. Override any of these per run with `--noise-figure-db <dB>`.

### "What if" re-runs — same site, different settings

| Scenario | Europe | Caribbean | S. America | Africa | Asia | Oceania |
|---|---|---|---|---|---|---|
| 1296 MHz, dish at surveyed spot (baseline) | 132 | 365 | 365 | 222 | 0 | 162 |
| 2304 MHz (13cm), same spot — min. elevation rises to 15° | 123 | 365 | 365 | 210 | 0 | 162 |
| 1296 MHz, dish moved 100ft **west** | 136 | 365 | 365 | 226 | 0 | **0** |

Moving the dish 100ft west closes the distance to the west hardwoods from 120ft to 20ft (atan(80/20) = 76° blockage) and wipes out Oceania entirely — a good demonstration of why "just move it a bit" needs to be checked, not assumed. Reproduce these with:
```bash
python src/eme_calculator.py --profile data/site_profiles/k2ua_fn12fr46wo.json --band 2304 --start-date 2026-01-01
python src/eme_calculator.py --profile data/site_profiles/k2ua_fn12fr46wo.json --offset-east-ft -100 --start-date 2026-01-01
```

## Building your own profile, step by step

1. **Get your coordinates and elevation.** `latitude`/`longitude` from a GPS reading or Google Maps; `elevation_ft` from USGS EPQS (`terrain.fetch_elevation_ft(lat, lon)`, needs internet) or any topo source.
2. **Walk (or view via satellite imagery) the horizon around your prospective antenna spot**, direction by direction. For each obstruction that matters, note: what it is, its height above the ground at the antenna (not sea level), its distance, and its bearing from the antenna.
3. **Decide line vs. cluster for each obstruction.** A hedgerow, fence line, or single row of trees is a `line_obstructions` entry — measure `perp_distance_ft`/`bearing_deg` to its nearest point and `line_bearing_deg` for the direction it runs, then either `half_length_ft` if it's roughly centered on that perpendicular foot point, or `along_line_start_ft`/`along_line_end_ft` if it isn't (see the K2UA west treeline above for a worked case of the latter). A stand or cluster with no clean line — a woodlot, an irregular tree mass — is easier as an `arc_obstructions` entry: just the azimuth span it covers plus one representative height/distance.
4. **Fill in `dem_octant_samples_ft`** with `terrain.fetch_octant_samples(lat, lon)` for a coarse regional floor, so azimuths without a surveyed near-field feature aren't silently treated as perfectly flat.
5. **Add `receiver_noise_figure_db`** for whichever bands you actually operate, at the antenna feedpoint (before feedline loss, after the preamp) — this is what the EME degradation ranking uses to pick each month's "best day." Bands you don't list fall back to a generic placeholder table; add real values as you get them.
6. **Run the CLI against your profile** and read the summary:
   ```bash
   python src/eme_calculator.py --profile data/site_profiles/your_site.json --band 1296
   ```
7. **Generate the plots and eyeball the wedge** (`scripts/generate_polar_plots.py`, `scripts/generate_monthly_track_plots.py` — see commands above). Confirm the gray wedge's shape matches what you'd actually expect standing at the site — a deep bite where you know there's a close treeline, shallow shading elsewhere. If it doesn't, recheck `bearing_deg` vs. `line_bearing_deg` (the most common mix-up) before trusting the pass counts.
8. **Check your target regions against your latitude's moonrise/moonset blind zone** ([above](#why-moonrise-and-moonset-arent-available-at-every-azimuth)) before spending more survey time on a direction — no obstruction model matters for a sector the Moon can never reach from your latitude in the first place.
9. **Iterate as better field data comes in.** Swap placeholders for real measurements, regenerate the plots, and check whether the change actually moves a pass count (it often doesn't move as much as the plot's shape suggests) before treating a re-survey as urgent.

## See also

- Main README's [Methodology & Limitations](../README.md#methodology--limitations) — the general pass-counting, terrain-modeling, and EME-degradation algorithms (not site-specific)
- Main README's [Rerunning for Other Scenarios](../README.md#rerunning-for-other-scenarios) — CLI flags for band/offset/date-range re-runs
- [`monthly_conditions.md`](monthly_conditions.md) — the full generated monthly tables for all six regions
