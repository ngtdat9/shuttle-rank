"""Pure single-elimination bracket math. No database access."""


def bracket_size(participants: int) -> int:
    """Smallest power of two that holds ``participants`` (at least 2)."""
    if participants < 2:
        raise ValueError("A bracket needs at least 2 participants")
    size = 2
    while size < participants:
        size *= 2
    return size


def round_count(size: int) -> int:
    """Number of rounds in a bracket of ``size`` slots (a power of two)."""
    rounds = 0
    while size > 1:
        size //= 2
        rounds += 1
    return rounds


def seed_order(size: int) -> list[int]:
    """Seed numbers in first-round slot order for a bracket of ``size``.

    Adjacent pairs meet in round 1. Seeds 1 and 2 sit in opposite halves, so
    they can only meet in the final, and the top seeds meet the lowest seeds.
    For 8: ``[1, 8, 4, 5, 2, 7, 3, 6]``.
    """
    order = [1]
    while len(order) < size:
        total = len(order) * 2
        order = [seed for top in order for seed in (top, total + 1 - top)]
    return order


def loser_position(round_number: int, max_round: int) -> int:
    """Final position for a player who lost in ``round_number``.

    Final loser 2, semifinal losers 3, quarterfinal losers 5, round-of-16
    losers 9, and so on: ``2 ** distance + 1``.
    """
    return 2 ** (max_round - round_number) + 1
