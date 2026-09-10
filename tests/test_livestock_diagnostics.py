"""Check descriptive care attribution against actual official refresh outcomes."""

import copy
import runpy
from pathlib import Path

import pytest

from kaggriculture_research.environment import game

ROOT = Path(__file__).resolve().parents[1]
DESCRIBE = runpy.run_path(str(ROOT / "scripts/diagnose_livestock_loops.py"))["describe"]


def test_absent_actions_keep_zero_events_in_the_group_mean():
    from kaggriculture_livestock.experiment import METRICS

    make = runpy.run_path(str(ROOT / "scripts/summarize_livestock.py"))["outcome_frame"]
    row = {metric: 0 for metric in METRICS}
    frame = make([{**row, "commands_FERTILIZE": 2}, row])
    assert frame.commands_FERTILIZE.mean() == 1
    missing = {k: v for k, v in row.items() if k != "match_score"}
    with pytest.raises(ValueError, match="registered outcome"):
        make([row, missing])


@pytest.mark.parametrize("animal", list(game.ANIMALS))
@pytest.mark.parametrize("fed", [False, True])
@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("prior_unfed", [0, 1])
def test_care_attribution_matches_official_production(animal, fed, full, prior_unfed):
    params = game.ANIMALS[animal]
    farm, private = game._new_farm(10, 3000), game._new_private()
    tile = game._new_animal(animal, 0)
    tile.update(
        fed_today=fed,
        cared_today=True,
        pending_care_bonus=2,
        consecutive_unfed=prior_unfed,
        yield_units=params["max_held"] if full else 0,
    )
    farm["tiles"][4][4] = tile
    day = params["first_yield_day"] - 1
    obs = {"farms": [farm, copy.deepcopy(farm)], "private": private, "day": day, "hour": 23}
    payload = {
        "summary": {"seat": 0},
        "records": [
            {
                "player": 0,
                "observation": obs,
                "action": {"farmer": ["PASS"], "hands": [], "market": []},
            }
        ],
        "accounting": {"products": [{p: {} for p in game.PRODUCTS}, {}]},
    }
    described, _ = DESCRIBE(payload)
    counts = next(r for r in described if r["species"] == animal)
    before = tile["yield_units"]
    game._daily_refresh_animals(farm, day)
    refreshed = farm["tiles"][4][4]
    escaped = "animal" not in refreshed
    assert counts["escaped_animals"] == int(escaped)
    if not escaped:
        assert counts["production_units"] == refreshed["yield_units"] - before
        assert counts["care_bank_additions"] == refreshed["pending_care_bonus"]
        assert counts["care_units_realized"] + counts["care_units_lost_capacity"] == (
            2 if fed else 0
        )
        assert counts["care_bank_lost_unfed"] == (0 if fed else 2)
