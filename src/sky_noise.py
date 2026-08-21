#!/usr/bin/env python3
"""
EME degradation model: sky (galactic) background noise + lunar-distance
path loss, combined into a single "degradation" figure in dB relative to
the best achievable conditions for a given band/receiver.

## Where this came from

The user supplied a methodology summary (paraphrased from WSJT-X / EME
community practice) with the core relationship:

    D_grd = -10*log10(Tsys / Tsysmin) + Dbmoon

Two things in that summary did not hold up against real references and
are corrected here, both confirmed via web research before implementing:

1. Sign: as written, D_grd goes NEGATIVE as conditions get worse (Tsys
   rising above Tsysmin makes the ratio >1, and -10*log10(>1) is
   negative), which contradicts the summary's own next line ("a result
   close to 0 dB indicates near-optimal conditions, while higher
   positive values indicate significant SNR loss"). This module drops
   the leading minus sign: D_grd = 10*log10(Tsys/Tsysmin) + Dbmoon, so
   D_grd is 0 dB at best-case conditions and grows positive as things
   get worse -- matching that description and matching "prioritize the
   lowest dB value" for best-day ranking.

2. Magnitude of Dbmoon (the lunar-distance/range term): the summary
   quoted "up to 12-14 dB between apogee and perigee." The actual
   two-way (round-trip, R^4) free-space path loss difference between
   mean lunar perigee (~356,500 km) and apogee (~406,700 km) is:

       40*log10(406700/356500) = ~2.3 dB

   which matches independently-published EME reference figures (e.g.
   MMMonVHF's EME calculator page states "as much as 2.25dB difference
   in pathloss from apogee to perigee"). The 12-14 dB range in the
   user's summary is almost certainly galactic sky-temperature swing
   (which really can be that large, especially at 144 MHz) misattributed
   to the distance term. See moon_range_factor_db() below -- it uses the
   correct ~2.3 dB physically-derived magnitude, not 12-14 dB.

3. Frequency direction: the summary said sky temperature "increases
   significantly at higher frequencies." Diffuse galactic synchrotron
   noise actually falls off steeply with frequency (published spectral
   index ~-2.5 to -2.75 in brightness temperature), so it is LOWEST at
   the higher microwave EME bands (1296 MHz and up, where it is only a
   few K above the 2.7K cosmic microwave background) and HIGHEST at
   144 MHz, where it can swing from ~20K to several thousand K
   depending on where in the sky the Moon is. This module scales sky
   temperature down with frequency accordingly (see sky_temperature_k).

## Sky (galactic) noise model

True pixel-accurate galactic noise maps (e.g. the real Haslam et al.
1982 408 MHz all-sky survey) require a real HEALPix map and are normally
consumed in Python via the `pygdsm` package -- which pulls in healpy,
h5py, astropy and scipy, and downloads ~500MB of survey data on first
use. That was evaluated and explicitly declined (see README Methodology
& Limitations / Revision History) in favor of a compact, dependency-free
alternative:

`data/sky_noise/galactic_408mhz_grid.json` is a SYNTHESIZED analytic
approximation -- not digitized survey pixels -- of the galactic 408 MHz
sky brightness temperature on a coarse 15deg x 15deg grid in galactic
coordinates. It reproduces the general shape any real map shows (a cold
off-plane floor, broad enhancement along the galactic disk, a strong
peak toward the galactic center, a secondary bump toward Cygnus X) with
landmark magnitudes calibrated to published order-of-magnitude values.
See that file's "_meta" field and generation formula for exact
parameters. If higher fidelity is ever wanted, swapping in `pygdsm` (or
hand-digitized real survey values in the same grid file) is a drop-in
upgrade -- nothing else in this module or its callers would need to
change.

Frequency scaling from 408 MHz to any other band uses ITU-R P.372-12
equation (15):

    Tb(fi) = Tb(f0) * (fi/f0)^-2.75 + 2.7 K

(2.7 K is the cosmic microwave background floor -- dominant at the
higher microwave EME bands where galactic synchrotron noise has fallen
to a few K.)
"""

import json
import math
import os
from typing import Dict, Tuple

_GRID_PATH = os.path.join(os.path.dirname(__file__), '..', 'data',
                           'sky_noise', 'galactic_408mhz_grid.json')

_T0_K = 290.0          # standard reference temperature for noise-figure <-> noise-temp conversion (IEEE/ITU convention)
_CMB_K = 2.7            # cosmic microwave background, Kelvin
_SPECTRAL_INDEX = -2.75  # ITU-R P.372-12 eq (15) brightness-temperature frequency scaling exponent
_F0_MHZ = 408.0          # reference frequency for the embedded grid

# Fixed reference distances (km, surface-to-surface-ish, standard
# published extreme values) used as the 0 dB (perigee) and worst-case
# (apogee) ends of the range factor. Fixed rather than derived from the
# analysis window, so results stay directly comparable across separate
# runs/bands/date ranges -- consistent with how min_elevation_for_band()
# and the terrain model are also fixed, run-independent references.
PERIGEE_REF_KM = 356500.0

_grid_cache = None


def _load_grid() -> Dict:
    global _grid_cache
    if _grid_cache is None:
        with open(_GRID_PATH) as f:
            _grid_cache = json.load(f)
    return _grid_cache


def _interp_1d(x, xs, ys, wrap=False, period=360.0):
    """Linear interpolation; if wrap, xs is assumed to span one period
    (e.g. galactic longitude 0..345 in 15deg steps covering 0..360)."""
    n = len(xs)
    if not wrap:
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        for i in range(n - 1):
            if xs[i] <= x <= xs[i + 1]:
                t = (x - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] * (1 - t) + ys[i + 1] * t
        return ys[-1]
    else:
        x = x % period
        for i in range(n):
            x0 = xs[i]
            x1 = xs[(i + 1) % n]
            step = x1 - x0 if i < n - 1 else period - x0
            if step <= 0:
                step = period - x0
            if x0 <= x < x0 + step or (i == n - 1 and x >= x0):
                t = (x - x0) / step if step else 0.0
                y0 = ys[i]
                y1 = ys[(i + 1) % n]
                return y0 * (1 - t) + y1 * t
        return ys[0]


def t408_k(galactic_lon_deg: float, galactic_lat_deg: float) -> float:
    """Bilinear-interpolated 408 MHz sky brightness temperature (K) at a
    galactic (longitude, latitude) direction, from the embedded
    synthesized grid (see module docstring)."""
    grid = _load_grid()
    lons = grid['longitude_deg']
    lats = grid['latitude_deg']
    table = grid['t408_k']

    lat_c = max(lats[0], min(lats[-1], galactic_lat_deg))
    # Find surrounding latitude rows and interpolate each in longitude
    # (wrapping), then interpolate the two results in latitude.
    if lat_c <= lats[0]:
        row_vals = table[0]
        return _interp_1d(galactic_lon_deg, lons, row_vals, wrap=True)
    if lat_c >= lats[-1]:
        row_vals = table[-1]
        return _interp_1d(galactic_lon_deg, lons, row_vals, wrap=True)

    for i in range(len(lats) - 1):
        if lats[i] <= lat_c <= lats[i + 1]:
            v0 = _interp_1d(galactic_lon_deg, lons, table[i], wrap=True)
            v1 = _interp_1d(galactic_lon_deg, lons, table[i + 1], wrap=True)
            t = (lat_c - lats[i]) / (lats[i + 1] - lats[i])
            return v0 * (1 - t) + v1 * t
    return table[-1][0]


def grid_min_t408_k() -> float:
    """Coldest 408 MHz sky temperature anywhere in the embedded grid --
    used as the reference direction for Tsysmin (best achievable sky)."""
    grid = _load_grid()
    return min(min(row) for row in grid['t408_k'])


def sky_temperature_k(frequency_mhz: float, galactic_lon_deg: float,
                       galactic_lat_deg: float) -> float:
    """Sky brightness temperature (K) at the given frequency and
    galactic direction: 408 MHz grid value scaled per ITU-R P.372-12 eq
    (15), plus the 2.7K CMB floor."""
    t408 = t408_k(galactic_lon_deg, galactic_lat_deg)
    return t408 * (frequency_mhz / _F0_MHZ) ** _SPECTRAL_INDEX + _CMB_K


def sky_temperature_min_k(frequency_mhz: float) -> float:
    """Best-case (coldest-sky-direction) sky temperature (K) at the
    given frequency -- the Tsysmin reference point."""
    t408_min = grid_min_t408_k()
    return t408_min * (frequency_mhz / _F0_MHZ) ** _SPECTRAL_INDEX + _CMB_K


def receiver_temp_k(noise_figure_db: float, t0_k: float = _T0_K) -> float:
    """Receiver noise temperature (K) from a noise figure in dB
    (standard IEEE/ITU relationship: NF_dB = 10*log10(1 + Te/T0))."""
    return t0_k * (10.0 ** (noise_figure_db / 10.0) - 1.0)


def moon_range_factor_db(distance_km: float,
                          perigee_km: float = PERIGEE_REF_KM) -> float:
    """Two-way (round-trip, R^4) free-space path loss in dB, relative to
    the fixed perigee reference distance. See module docstring for why
    this is ~2.3 dB max (apogee to perigee), not the 12-14 dB the user's
    original notes suggested."""
    if distance_km <= perigee_km:
        return 0.0
    return 40.0 * math.log10(distance_km / perigee_km)


def degradation_db(frequency_mhz: float, galactic_lon_deg: float,
                    galactic_lat_deg: float, distance_km: float,
                    noise_figure_db: float) -> Tuple[float, Dict]:
    """EME degradation in dB (0 = best achievable conditions for this
    band/receiver, higher = worse) plus a breakdown dict for
    transparency/reporting. See module docstring for the corrected
    formula and its derivation from the user-supplied methodology."""
    tsky = sky_temperature_k(frequency_mhz, galactic_lon_deg, galactic_lat_deg)
    tsky_min = sky_temperature_min_k(frequency_mhz)
    tr = receiver_temp_k(noise_figure_db)
    tsys = tsky + tr
    tsysmin = tsky_min + tr
    range_db = moon_range_factor_db(distance_km)
    base_db = 10.0 * math.log10(tsys / tsysmin)
    total_db = base_db + range_db
    breakdown = {
        'sky_temp_k': tsky,
        'sky_temp_min_k': tsky_min,
        'receiver_temp_k': tr,
        'tsys_k': tsys,
        'tsys_min_k': tsysmin,
        'sky_noise_db': base_db,
        'range_factor_db': range_db,
    }
    return total_db, breakdown
