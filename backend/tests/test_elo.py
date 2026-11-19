"""Elo formula tests. Expected deltas are computed from decision D-007."""

import random

import pytest

from app.services.elo import (
    K_FACTOR,
    SCALE,
    STARTING_RATING,
    apply_result,
    expected_score,
    rating_delta,
)


def test_constants() -> None:
    assert STARTING_RATING == 1500
    assert K_FACTOR == 32
    assert SCALE == 400


def test_equal_ratings_move_sixteen_points() -> None:
    result = apply_result(1500, 1500)
    assert result.delta == 16
    assert result.winner_new == 1516
    assert result.loser_new == 1484
    assert expected_score(1500, 1500) == pytest.approx(0.5)


def test_stronger_winner_gains_fewer_than_sixteen() -> None:
    # 1600 vs 1400: raw delta is about 7.69, which rounds half up to 8.
    result = apply_result(1600, 1400)
    assert result.delta == 8
    assert result.delta < 16
    assert result.winner_new == 1608
    assert result.loser_new == 1392


def test_weaker_winner_gains_more_than_sixteen() -> None:
    # 1400 vs 1600: raw delta is about 24.31, which rounds half up to 24.
    result = apply_result(1400, 1600)
    assert result.delta == 24
    assert result.delta > 16
    assert result.winner_new == 1424
    assert result.loser_new == 1576


def test_expected_scores_sum_to_one() -> None:
    assert expected_score(1600, 1400) + expected_score(1400, 1600) == pytest.approx(1.0)
    assert expected_score(1600, 1400) == pytest.approx(1 / (1 + 10 ** (-200 / 400)))


def test_round_half_up_at_exact_half() -> None:
    # Equal ratings make the expected score exactly 0.5, so the raw delta is k/2.
    # k=33 produces 16.5. Half-up yields 17. Python round(16.5) is 16 (banker's).
    assert round(16.5) == 16
    assert rating_delta(1500, 1500, k=33) == 17


def test_random_pairs_are_zero_sum() -> None:
    rng = random.Random(7)
    for _ in range(200):
        winner_rating = rng.randint(800, 2200)
        loser_rating = rng.randint(800, 2200)
        result = apply_result(winner_rating, loser_rating)
        assert result.delta == rating_delta(winner_rating, loser_rating)
        assert result.winner_new == winner_rating + result.delta
        assert result.loser_new == loser_rating - result.delta
        assert result.winner_new + result.loser_new == winner_rating + loser_rating
        assert result.delta >= 0
