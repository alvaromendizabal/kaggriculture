from __future__ import annotations

from kaggriculture_adaptive.policy import (
    AdaptiveOverlay,
    _effective_step,
    impact_loss,
    market_price,
    rank_existing_sell_slots,
)


def observation(step: int = 0, hands: int = 0) -> dict:
    farms = []
    for _ in (0, 1):
        farms.append(
            {
                "money": 10000,
                "hands": [[2, 2] for _ in range(hands)],
                "farmer": [2, 2],
                "unlocked_quadrants": [0, 1, 2],
                "tiles": [[None for _ in range(5)] for _ in range(5)],
            }
        )
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": farms,
        "private": {
            "shed": {"MELON": 10, "MILK": 10},
            "inventories": [{} for _ in range(1 + hands)],
        },
        "market": {
            "inventory": {
                key: 10000
                for key in (
                    "WHEAT",
                    "CARROT",
                    "TOMATO",
                    "STRAWBERRY",
                    "MELON",
                    "EGG",
                    "MILK",
                    "WOOL",
                    "FERTILIZER",
                )
            },
            "prices": {},
        },
        "town": {"unlocked_shops": []},
    }


def test_market_curve_is_exactly_bounded_and_nonlinear() -> None:
    assert market_price("MELON", 10000) == 250
    assert 1 <= market_price("MELON", 10500) < market_price("MELON", 10000)
    assert impact_loss("MELON", 10000, 20) > impact_loss("WHEAT", 10000, 20)


def test_existing_sell_slots_are_ranked_without_moving_non_sell_orders() -> None:
    action = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [
            ["BUY_SEED", "WHEAT", 1],
            ["SELL", "WHEAT", 5],
            ["HIRE"],
            ["SELL", "MELON", 10],
        ],
    }
    ranked, changed = rank_existing_sell_slots(observation(), action)
    assert changed
    assert ranked["market"][0] == ["BUY_SEED", "WHEAT", 1]
    assert ranked["market"][2] == ["HIRE"]
    assert ranked["market"][1][1] == "MELON"
    assert ranked["market"][3][1] == "WHEAT"


def test_clone_front_run_repays_quantity_on_next_turn() -> None:
    route = [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(30)]
    route[24] = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "MELON", 4]],
    }

    def base_agent(obs: dict, config=None) -> dict:
        return route[obs["step"]]

    policy = AdaptiveOverlay(base_agent, route, "clone_front_run")
    policy.state[0].clone_confidence = 2

    early = policy(observation(step=23))
    assert ["SELL", "MELON", 4] in early["market"]
    assert policy.state[0].due_step == 24

    repayment = policy(observation(step=24))
    assert ["SELL", "MELON", 4] not in repayment["market"]
    assert policy.diagnostics["repaid_units"] == 4


def test_overlay_does_not_consume_environment_seed_or_future_state() -> None:
    source = __import__("inspect").getsource(AdaptiveOverlay)
    assert '["seed"]' not in source
    assert "future_shops" not in source

def test_effective_step_uses_day_hour_when_seat_one_step_is_missing() -> None:
    obs = observation(step=29)
    obs["player"] = 1
    obs.pop("step")
    assert _effective_step(obs) == 29


def test_effective_step_prefers_synced_clock_over_stale_zero_step() -> None:
    obs = observation(step=719)
    obs["player"] = 1
    obs["step"] = 0
    assert _effective_step(obs) == 719


def test_player_one_overlay_state_advances_without_step_field() -> None:
    def base_agent(obs: dict, config=None) -> dict:
        return {"farmer": ["PASS"], "hands": [], "market": []}

    policy = AdaptiveOverlay(base_agent, [], "impact_slots")
    for step in (0, 1, 4, 24):
        obs = observation(step=step)
        obs["player"] = 1
        obs.pop("step")
        policy(obs)

    assert policy.state[1].last_step == 24


def test_player_one_terminal_guard_uses_day_hour_clock() -> None:
    def base_agent(obs: dict, config=None) -> dict:
        return {"farmer": ["PASS"], "hands": [], "market": []}

    policy = AdaptiveOverlay(base_agent, [], "clone_terminal")
    obs = observation(step=717)
    obs["player"] = 1
    obs.pop("step")
    policy(obs)

    assert policy.state[1].last_step == 717
    assert policy.diagnostics["terminal_guard_steps"] == 1

