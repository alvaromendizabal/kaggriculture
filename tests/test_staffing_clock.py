"""Pinned-engine regression tests for staffing-study callback chronology."""

from kaggriculture_research.environment import game, make_environment
from kaggriculture_staffing.features import canonical_observation


def test_pinned_engine_callbacks_normalize_to_full_clock_for_both_seats():
    seen = {0: [], 1: []}

    def capture(observation, configuration):
        if configuration.get("seed") is not None:
            raise ValueError("Seed leaked into callback configuration")
        obs = canonical_observation(observation)
        seen[obs["player"]].append((obs["step"], obs["day"], obs["hour"]))
        return game.pass_agent(observation)

    env = make_environment(1599, {"episodeSteps": 720})
    env.run([capture, capture])
    assert [state.status for state in env.state] == ["DONE", "DONE"]
    for player in (0, 1):
        assert [step for step, _, _ in seen[player]] == list(range(719))
        assert all(step == day * 24 + hour for step, day, hour in seen[player])


def test_missing_step_value_uses_day_hour_and_conflicts_fail_closed():
    env = make_environment(1599, {"episodeSteps": 720})
    env.reset()
    observation = dict(env.state[0].observation)
    observation["step"] = None
    normalized = canonical_observation(observation)
    assert normalized["step"] == normalized["day"] * 24 + normalized["hour"]

    observation["step"] = normalized["step"] + 1
    try:
        canonical_observation(observation)
    except ValueError as error:
        assert "canonical day/hour clock" in str(error)
    else:
        raise AssertionError("Conflicting non-null step must fail closed")
