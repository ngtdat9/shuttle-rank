"""Pure Elo calculation. This module does not touch the database.

Starting rating is 1500, K is 32, and the scale divisor is 400. One integer
delta is taken from the winner's perspective and applied symmetrically:
winner gains ``delta``, loser loses ``delta``.

Rounding (decision D-007) is half up, not Python's banker's ``round``:

    delta = floor(K * (1 - expected_score(winner, loser)) + 0.5)

Equal 1500 ratings produce +16 / -16 because the expected score is 0.5 and
``floor(32 * 0.5 + 0.5)`` is 16.
"""

import math
from dataclasses import dataclass

STARTING_RATING = 1500
K_FACTOR = 32
SCALE = 400


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probability that a player rated ``rating_a`` beats ``rating_b``.

    ``1 / (1 + 10 ** ((rating_b - rating_a) / 400))``.
    """
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / SCALE))


def rating_delta(winner_rating: float, loser_rating: float, k: float = K_FACTOR) -> int:
    """Integer points transferred from the loser to the winner.

    ``floor(k * (1 - expected_score(winner, loser)) + 0.5)`` rounds half up
    away from zero for the positive winner-side delta. The same integer is
    later subtracted from the loser, so the exchange stays zero-sum even when
    the raw value lands on ``n.5``. Python's built-in ``round`` would use
    banker's rounding there (for example ``round(16.5) == 16``); this function
    returns 17 for that input.
    """
    expected = expected_score(winner_rating, loser_rating)
    return math.floor(k * (1.0 - expected) + 0.5)


@dataclass(frozen=True)
class EloResult:
    """Ratings after one completed match and the shared integer delta."""

    winner_new: int
    loser_new: int
    delta: int


def apply_result(winner_rating: int, loser_rating: int) -> EloResult:
    """Apply one symmetric delta to the pre-match ratings.

    ``winner_new = winner_rating + delta`` and ``loser_new = loser_rating - delta``.
    """
    delta = rating_delta(winner_rating, loser_rating)
    return EloResult(
        winner_new=winner_rating + delta,
        loser_new=loser_rating - delta,
        delta=delta,
    )
