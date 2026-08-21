"""End-to-end regression test for scripts/build_site_profile.py: drives
the interactive wizard with a scripted sequence of answers exercising
every obstruction-entry method (manual, two lat/lon points, two pixel
points), then checks the resulting profile JSON is well-formed and
loads cleanly through TerrainProfile.

If a prompt's wording changes without updating this test's answer
sequence, later answers land on the wrong prompts and the run either
exits non-zero or produces an obviously wrong profile -- both are
caught below, which is the point: this test is what would have caught
the FT_PER_M unit bug and the missing-blank-line desync found by hand
while building this wizard.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from terrain import TerrainProfile

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPT = os.path.join(REPO_ROOT, 'scripts', 'build_site_profile.py')

ANSWERS = [
    "Test Site",                 # profile_name
    "y",                         # enter as grid square?
    "FN12fr46wo",                # grid
    "y",                         # use computed coordinates?
    "n",                         # auto-fetch elevation? (no network in CI)
    "1573.88",                   # elevation_ft, manual
    "12",                        # antenna_agl_ft
    "test notes here",           # notes
    # obstruction 1: line via two lat/lon points
    "line", "West test row", "", "80", "latlon",
    "42.736913", "-77.5450", "42.734913", "-77.5450",
    # obstruction 2: line via manual entry, asymmetric extent
    "line", "East test row", "some pines", "45", "manual",
    "200", "90", "0", "n", "-100", "150",
    # obstruction 3: arc via two pixel points
    "arc", "Test cluster", "", "70", "pixel",
    "19", "500", "500", "600", "500", "650", "550",
    "done",
    # noise figures: 144, 432, 902, 1296, 2304, 3456, 5760, 10368
    "0.5", "0.5", "", "0.3", "0.4", "", "", "0.9",
    "n",                          # auto-fetch DEM floor? (no network in CI)
    "test_site_wizard",           # output filename (no .json -- exercise that the
                                   # wizard doesn't require the extension either way)
    "n",                          # generate plots now?
]


@pytest.fixture
def wizard_output_path():
    out_path = os.path.join(REPO_ROOT, 'data', 'site_profiles', 'test_site_wizard')
    if os.path.exists(out_path):
        os.unlink(out_path)
    yield out_path
    if os.path.exists(out_path):
        os.unlink(out_path)


def test_wizard_produces_a_valid_profile(wizard_output_path):
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input="\n".join(ANSWERS) + "\n",
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"wizard exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert "Please answer" not in proc.stdout, (
        "a prompt got re-asked -- the answer sequence desynced from the actual prompts:\n" + proc.stdout)
    assert "Not a number" not in proc.stdout, "a numeric prompt got a non-numeric answer:\n" + proc.stdout
    assert os.path.exists(wizard_output_path), proc.stdout

    with open(wizard_output_path) as f:
        profile = json.load(f)

    assert profile["profile_name"] == "Test Site"
    assert profile["grid_square"] == "FN12fr46wo"
    assert profile["elevation_ft"] == pytest.approx(1573.88)
    assert profile["antenna_agl_ft"] == pytest.approx(12.0)
    assert profile["notes"] == "test notes here"

    assert len(profile["line_obstructions"]) == 2
    west = next(f for f in profile["line_obstructions"] if f["name"] == "West test row")
    assert west["height_ft"] == pytest.approx(80.0)
    assert west["bearing_deg"] == pytest.approx(270.0, abs=1.0)  # due west, per the chosen test points

    east = next(f for f in profile["line_obstructions"] if f["name"] == "East test row")
    assert east["description"] == "some pines"
    assert east["perp_distance_ft"] == pytest.approx(200.0)
    assert east["along_line_start_ft"] == pytest.approx(-100.0)
    assert east["along_line_end_ft"] == pytest.approx(150.0)
    assert "half_length_ft" not in east  # asymmetric entry was chosen

    assert len(profile["arc_obstructions"]) == 1
    cluster = profile["arc_obstructions"][0]
    assert cluster["height_ft"] == pytest.approx(70.0)
    assert cluster["az_start_deg"] < cluster["az_end_deg"]

    nf = profile["receiver_noise_figure_db"]
    assert nf["144"] == pytest.approx(0.5)
    assert nf["1296"] == pytest.approx(0.3)
    assert "902" not in nf  # left blank

    # The whole point: the wizard's output has to actually load and
    # evaluate through the real terrain model without error.
    tp = TerrainProfile(wizard_output_path)
    angle_at_west = tp.horizon_angle_deg(west["bearing_deg"])
    assert angle_at_west > 0, "the west tree row should register as an obstruction at its own bearing"
