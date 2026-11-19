"""Tournament admin API: bracket generation, results, corrections, audit, auth."""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.rate_limit import failed_auth_limiter
from app.models.audit_log import AuditLog
from app.models.tournament import TournamentParticipant
from app.services.bracket import bracket_size, loser_position, seed_order

ApiClient = tuple[TestClient, sessionmaker[Session]]


@pytest.fixture(autouse=True)
def _reset_auth_limiter() -> Iterator[None]:
    failed_auth_limiter.reset()
    yield
    failed_auth_limiter.reset()


def _h() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def _players(client: TestClient, count: int) -> list[str]:
    ids = []
    for index in range(1, count + 1):
        response = client.post(
            "/api/v1/admin/players", json={"display_name": f"P{index}"}, headers=_h()
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


def _tournament(client: TestClient, players: list[str], **body: Any) -> str:
    response = client.post("/api/v1/admin/tournaments", json={"name": "Open", **body}, headers=_h())
    assert response.status_code == 201, response.json()
    tid = response.json()["id"]
    assert response.json()["status"] == "draft"
    added = client.post(
        f"/api/v1/admin/tournaments/{tid}/participants",
        json={"participants": [{"player_id": pid} for pid in players]},
        headers=_h(),
    )
    assert added.status_code == 200, added.json()
    return tid


def _generate(client: TestClient, tid: str, **body: Any) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/admin/tournaments/{tid}/generate-bracket", json=body, headers=_h()
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _bracket(client: TestClient, tid: str) -> dict[str, Any]:
    return client.get(f"/api/v1/tournaments/{tid}/bracket").json()


def _slot(bracket: dict[str, Any], round_number: int, position: int) -> dict[str, Any]:
    for rnd in bracket["rounds"]:
        if rnd["round"] == round_number:
            return rnd["matches"][position]
    raise AssertionError("round not found")


_DAY = {"n": 0}


def _play(
    client: TestClient,
    tid: str,
    round_number: int,
    position: int,
    winner: str = "a",
    **extra: Any,
) -> Any:
    slot = _slot(_bracket(client, tid), round_number, position)
    winner_id = slot["player_a" if winner == "a" else "player_b"]["id"]
    _DAY["n"] += 1
    return client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": slot["id"],
            "winner_id": winner_id,
            "match_date": f"2026-10-{_DAY['n'] % 27 + 1:02d}T10:00:00Z",
            **extra,
        },
        headers=_h(),
    )


def _names(slot: dict[str, Any]) -> tuple[str | None, str | None]:
    return (
        slot["player_a"] and slot["player_a"]["display_name"],
        slot["player_b"] and slot["player_b"]["display_name"],
    )


def _detail(client: TestClient, tid: str) -> dict[str, Any]:
    return client.get(f"/api/v1/tournaments/{tid}").json()


def _actions(factory: sessionmaker[Session]) -> list[str]:
    with factory() as db:
        return [row.action for row in db.scalars(select(AuditLog).order_by(AuditLog.created_at))]


def test_bracket_math() -> None:
    assert bracket_size(2) == 2 and bracket_size(3) == 4 and bracket_size(5) == 8
    assert bracket_size(8) == 8 and bracket_size(9) == 16
    assert seed_order(2) == [1, 2]
    assert seed_order(4) == [1, 4, 2, 3]
    assert seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    for size in (4, 8, 16, 32):
        order = seed_order(size)
        half = size // 2
        assert {1, 2} <= set(order) and (order.index(1) < half) != (order.index(2) < half)
        assert all(order[i] + order[i + 1] == size + 1 for i in range(0, size, 2))
    assert [loser_position(r, 4) for r in (4, 3, 2, 1)] == [2, 3, 5, 9]
    with pytest.raises(ValueError):
        bracket_size(1)


def test_two_participants_single_final(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 2)
    tid = _tournament(client, players)
    bracket = _generate(client, tid)
    assert [r["name"] for r in bracket["rounds"]] == ["Final"]
    final = _slot(bracket, 1, 0)
    assert final["status"] == "ready" and not final["is_bye"]
    assert _names(final) == ("P1", "P2") and (final["seed_a"], final["seed_b"]) == (1, 2)
    assert _detail(client, tid)["status"] == "in_progress"


def test_three_participants_bye_and_seeding(api_client: ApiClient) -> None:
    client, _ = api_client
    tid = _tournament(client, _players(client, 3))
    bracket = _generate(client, tid)
    assert [r["name"] for r in bracket["rounds"]] == ["Semifinals", "Final"]
    bye = _slot(bracket, 1, 0)
    assert bye["is_bye"] and bye["status"] == "bye" and _names(bye) == ("P1", None)
    assert bye["winner_id"] == bye["player_a"]["id"]
    assert _names(_slot(bracket, 1, 1)) == ("P2", "P3")
    final = _slot(bracket, 2, 0)
    assert _names(final) == ("P1", None) and final["status"] == "pending"


def test_five_participants_top_seeds_get_byes(api_client: ApiClient) -> None:
    client, _ = api_client
    tid = _tournament(client, _players(client, 5))
    bracket = _generate(client, tid)
    assert [r["name"] for r in bracket["rounds"]] == ["Quarterfinals", "Semifinals", "Final"]
    round1 = bracket["rounds"][0]["matches"]
    assert [m["is_bye"] for m in round1] == [True, False, True, True]
    assert [_names(m) for m in round1] == [("P1", None), ("P4", "P5"), ("P2", None), ("P3", None)]
    # byes advanced: seeds 1 and 2 are in opposite halves
    semis = bracket["rounds"][1]["matches"]
    assert _names(semis[0]) == ("P1", None)
    assert _names(semis[1]) == ("P2", "P3")


def test_rating_seeding_and_manual_seeding(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 4)
    # P4 beats P1: P4 now rates above P1 (and P2/P3 stay 1500).
    client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": players[0],
            "player_b_id": players[3],
            "winner_id": players[3],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    )
    tid = _tournament(client, players)
    bracket = _generate(client, tid, seeding="rating")
    # P4 (1516) seed 1, then P2, P3 (1500), P1 (1484) last.
    assert _names(_slot(bracket, 1, 0)) == ("P4", "P1")
    assert _names(_slot(bracket, 1, 1)) == ("P2", "P3")

    # Regenerate before any result with manual seeds; unseeded go last by rating.
    draft = client.post("/api/v1/admin/tournaments", json={"name": "Manual"}, headers=_h()).json()
    seeds = {players[2]: 1, players[1]: 2}
    response = client.post(
        f"/api/v1/admin/tournaments/{draft['id']}/participants",
        json={"participants": [{"player_id": pid, "seed": seeds.get(pid)} for pid in players]},
        headers=_h(),
    )
    assert response.status_code == 200
    manual = _generate(client, draft["id"], seeding="manual")
    assert _names(_slot(manual, 1, 0)) == ("P3", "P1")  # seed1 v seed4 (P1 lowest rating)
    assert _names(_slot(manual, 1, 1)) == ("P2", "P4")
    seeds_out = {
        p["player"]["display_name"]: p["seed"] for p in _detail(client, draft["id"])["participants"]
    }
    assert seeds_out == {"P3": 1, "P2": 2, "P4": 3, "P1": 4}


def test_full_eight_player_run_positions_and_elo(api_client: ApiClient) -> None:
    client, factory = api_client
    tid = _tournament(client, _players(client, 8))
    _generate(client, tid)
    first = _play(client, tid, 1, 0, "a", game_scores=[[21, 10], [21, 15]])
    assert first.status_code == 201, first.json()
    body = first.json()
    assert body["match"]["tournament"]["name"] == "Open"
    # Same Elo as a club match between two 1500 players.
    assert sorted(c["rating_change"] for c in body["match"]["rating_changes"]) == [-16, 16]
    assert _slot(body["bracket"], 1, 0)["status"] == "completed"
    assert _slot(body["bracket"], 2, 0)["player_a"]["display_name"] == "P1"
    for position in (1, 2, 3):
        assert _play(client, tid, 1, position, "a").status_code == 201
    assert _detail(client, tid)["status"] == "in_progress"
    assert _play(client, tid, 2, 0, "a").status_code == 201
    assert _play(client, tid, 2, 1, "b").status_code == 201
    final = _play(client, tid, 3, 0, "a")
    assert final.status_code == 201
    detail = _detail(client, tid)
    assert detail["status"] == "completed"
    assert detail["champion"]["display_name"] == "P1"
    positions = {p["player"]["display_name"]: p["final_position"] for p in detail["participants"]}
    # QF winners: P1, P4, P2, P3. SF: P1 beat P4; P3 (pos b) beat P2. Final: P1 beat P3.
    assert positions["P1"] == 1
    assert detail["runner_up"]["display_name"] == "P3"
    assert positions["P3"] == 2
    assert {positions["P4"], positions["P2"]} == {3}
    assert {positions["P8"], positions["P5"], positions["P7"], positions["P6"]} == {5}
    # recorded results cannot be re-recorded
    again = client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": _slot(_bracket(client, tid), 3, 0)["id"],
            "winner_id": _slot(_bracket(client, tid), 3, 0)["player_a"]["id"],
            "match_date": "2026-10-02T10:00:00Z",
        },
        headers=_h(),
    )
    assert again.status_code == 409
    actions = _actions(factory)
    assert actions.count("tournament.match_record") == 7
    assert actions.count("match.create") == 7


def test_elo_same_as_club_match(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 4)
    club = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": players[0],
            "player_b_id": players[1],
            "winner_id": players[0],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    ).json()
    tid = _tournament(client, players[2:])
    _generate(client, tid)
    response = _play(client, tid, 1, 0, "a")
    changes = response.json()["match"]["rating_changes"]
    assert sorted(c["rating_change"] for c in changes) == sorted(
        c["rating_change"] for c in club["rating_changes"]
    )
    assert _detail(client, tid)["status"] == "completed"


def test_record_validation(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 4)
    tid = _tournament(client, players)
    draft_slot = {
        "bracket_match_id": players[0],
        "winner_id": players[0],
        "match_date": "2026-10-01T10:00:00Z",
    }
    assert (
        client.post(
            f"/api/v1/admin/tournaments/{tid}/matches", json=draft_slot, headers=_h()
        ).status_code
        == 409
    )
    bracket = _generate(client, tid)
    final = _slot(bracket, 2, 0)
    pending = client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": final["id"],
            "winner_id": players[0],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    )
    assert (
        pending.status_code == 422 and pending.json()["error"]["code"] == "business_rule_violation"
    )
    semi = _slot(bracket, 1, 0)
    wrong = client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": semi["id"],
            "winner_id": players[1],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    )
    assert wrong.status_code == 422
    missing = client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": "00000000-0000-0000-0000-000000000000",
            "winner_id": players[0],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    )
    assert missing.status_code == 404
    # nothing was rated
    assert client.get(f"/api/v1/players/{players[0]}").json()["current_rating"] == 1500


def test_regenerate_rules_and_participant_locks(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 4)
    lonely = _tournament(client, players[:1])
    resp = client.post(
        f"/api/v1/admin/tournaments/{lonely}/generate-bracket", json={}, headers=_h()
    )
    assert resp.status_code == 422
    tid = _tournament(client, players)
    first = _generate(client, tid)
    again = _generate(client, tid, seeding="rating")  # in_progress, no result: allowed
    assert _slot(again, 1, 0)["id"] != _slot(first, 1, 0)["id"]
    assert len(again["rounds"]) == 2
    # locked participants
    assert (
        client.post(
            f"/api/v1/admin/tournaments/{tid}/participants",
            json={"participants": [{"player_id": players[0]}]},
            headers=_h(),
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/admin/tournaments/{tid}/participants/{players[0]}", headers=_h()
        ).status_code
        == 409
    )
    assert _play(client, tid, 1, 0, "a").status_code == 201
    blocked = client.post(
        f"/api/v1/admin/tournaments/{tid}/generate-bracket", json={}, headers=_h()
    )
    assert blocked.status_code == 409
    # bye-only auto-advancement doesn't count as a result: 3 players, regenerate fine
    three = _tournament(client, players[:3])
    _generate(client, three)
    _generate(client, three)


def test_cancel_correct_delete_rules(api_client: ApiClient) -> None:
    client, factory = api_client
    players = _players(client, 4)
    tid = _tournament(client, players)
    _generate(client, tid)
    semi0 = _play(client, tid, 1, 0, "a").json()["match"]  # P1 beats P4
    semi1 = _play(client, tid, 1, 1, "a").json()["match"]  # P2 beats P3
    # Change the winner of semifinal 0 while the final has no result.
    fixed = client.post(
        f"/api/v1/admin/matches/{semi0['id']}/correct",
        json={"winner_id": semi0["player_b"]["id"], "reason": "wrong winner"},
        headers=_h(),
    )
    assert fixed.status_code == 200, fixed.json()
    final = _slot(_bracket(client, tid), 2, 0)
    assert _names(final) == ("P4", "P2") and final["status"] == "ready"
    # Players cannot be changed.
    swap = client.post(
        f"/api/v1/admin/matches/{semi0['id']}/correct",
        json={"player_a_id": players[2], "reason": "swap"},
        headers=_h(),
    )
    assert swap.status_code == 422
    # Record the final, then block upstream changes with 422 and no side effects.
    assert _play(client, tid, 2, 0, "a").status_code == 201
    before = {p: client.get(f"/api/v1/players/{p}").json()["current_rating"] for p in players}
    for call in (
        lambda: client.post(
            f"/api/v1/admin/matches/{semi1['id']}/cancel", json={"reason": "rain"}, headers=_h()
        ),
        lambda: client.delete(
            f"/api/v1/admin/matches/{semi1['id']}", params={"reason": "void"}, headers=_h()
        ),
        lambda: client.post(
            f"/api/v1/admin/matches/{semi1['id']}/correct",
            json={"winner_id": semi1["player_b"]["id"], "reason": "oops"},
            headers=_h(),
        ),
    ):
        response = call()
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "business_rule_violation"
    assert before == {
        p: client.get(f"/api/v1/players/{p}").json()["current_rating"] for p in players
    }
    assert _slot(_bracket(client, tid), 1, 1)["status"] == "completed"
    assert client.get(f"/api/v1/matches/{semi1['id']}").json()["status"] == "completed"
    assert _detail(client, tid)["status"] == "completed"

    # Cancel the final: tournament reopens, positions clear, slot is ready.
    final_match = _slot(_bracket(client, tid), 2, 0)["match_id"]
    canceled = client.post(
        f"/api/v1/admin/matches/{final_match}/cancel", json={"reason": "replay"}, headers=_h()
    )
    assert canceled.status_code == 200
    detail = _detail(client, tid)
    assert detail["status"] == "in_progress" and detail["champion"] is None
    assert all(p["final_position"] is None for p in detail["participants"])
    final = _slot(_bracket(client, tid), 2, 0)
    assert final["status"] == "ready" and final["match_id"] is None
    # Canceled result is not rated.
    assert {p: client.get(f"/api/v1/players/{p}").json()["current_rating"] for p in players}
    # Re-record the final, then correct it back (final winner swap updates positions).
    redo = _play(client, tid, 2, 0, "b")
    assert redo.status_code == 201
    assert _detail(client, tid)["champion"]["display_name"] == "P2"
    redo_match = redo.json()["match"]
    swap_final = client.post(
        f"/api/v1/admin/matches/{redo_match['id']}/correct",
        json={"winner_id": redo_match["player_a"]["id"], "reason": "wrong final winner"},
        headers=_h(),
    )
    assert swap_final.status_code == 200
    detail = _detail(client, tid)
    assert (
        detail["champion"]["display_name"] == "P4" and detail["runner_up"]["display_name"] == "P2"
    )
    # Delete a semifinal is blocked while the final has a result; delete the final first.
    deleted = client.delete(
        f"/api/v1/admin/matches/{redo_match['id']}", params={"reason": "void"}, headers=_h()
    )
    assert deleted.status_code == 200
    assert _detail(client, tid)["status"] == "in_progress"
    # Now a semifinal can be canceled; the slot returns to ready and the final loses a player.
    ok = client.post(
        f"/api/v1/admin/matches/{semi1['id']}/cancel", json={"reason": "rain"}, headers=_h()
    )
    assert ok.status_code == 200
    bracket = _bracket(client, tid)
    assert _slot(bracket, 1, 1)["status"] == "ready"
    final = _slot(bracket, 2, 0)
    assert _names(final) == ("P4", None) and final["status"] == "pending"
    # Reinstating the canceled semifinal re-attaches it to the open bracket match.
    back = client.post(
        f"/api/v1/admin/matches/{semi1['id']}/correct",
        json={"status": "completed", "reason": "rain stopped"},
        headers=_h(),
    )
    assert back.status_code == 200, back.json()
    bracket = _bracket(client, tid)
    assert _slot(bracket, 1, 1)["status"] == "completed"
    assert _slot(bracket, 1, 1)["match_id"] == semi1["id"]
    assert _names(_slot(bracket, 2, 0))[1] == "P2"
    actions = _actions(factory)
    assert "match.cancel" in actions and "match.delete" in actions and "match.correct" in actions


def test_participants_endpoints(api_client: ApiClient) -> None:
    client, factory = api_client
    players = _players(client, 3)
    client.patch(f"/api/v1/admin/players/{players[2]}", json={"is_active": False}, headers=_h())
    tid = client.post("/api/v1/admin/tournaments", json={"name": " Spring "}, headers=_h()).json()[
        "id"
    ]
    url = f"/api/v1/admin/tournaments/{tid}/participants"
    assert (
        client.post(
            url, json={"participants": [{"player_id": players[0], "seed": 1}]}, headers=_h()
        ).status_code
        == 200
    )
    dup = client.post(url, json={"participants": [{"player_id": players[0]}]}, headers=_h())
    assert dup.status_code == 409
    inactive = client.post(url, json={"participants": [{"player_id": players[2]}]}, headers=_h())
    assert inactive.status_code == 422
    unknown = client.post(
        url,
        json={"participants": [{"player_id": "00000000-0000-0000-0000-000000000000"}]},
        headers=_h(),
    )
    assert unknown.status_code == 422
    same_seed = client.post(
        url, json={"participants": [{"player_id": players[1], "seed": 1}]}, headers=_h()
    )
    assert same_seed.status_code == 422
    empty = client.post(url, json={"participants": []}, headers=_h())
    assert empty.status_code == 422 and empty.json()["error"]["code"] == "validation_error"
    assert (
        client.post(
            url, json={"participants": [{"player_id": players[1]}]}, headers=_h()
        ).status_code
        == 200
    )
    removed = client.delete(f"{url}/{players[1]}", headers=_h())
    assert removed.status_code == 200 and removed.json()["participant_count"] == 1
    assert client.delete(f"{url}/{players[1]}", headers=_h()).status_code == 404
    assert client.get(f"/api/v1/tournaments/{tid}").json()["name"] == "Spring"
    assert _actions(factory).count("tournament.participants_add") == 2


def test_create_and_patch_tournament(api_client: ApiClient) -> None:
    client, factory = api_client
    created = client.post(
        "/api/v1/admin/tournaments",
        json={
            "name": "Cup",
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "description": "d",
        },
        headers=_h(),
    )
    assert created.status_code == 201
    tid = created.json()["id"]
    assert created.json()["bracket_generated"] is False
    for bad in (
        {"name": ""},
        {"name": "x" * 101},
        {"name": "ok", "rating": 5},
        {"name": "ok", "start_date": "2026-11-05", "end_date": "2026-11-01"},
    ):
        response = client.post("/api/v1/admin/tournaments", json=bad, headers=_h())
        assert response.status_code == 422
    patched = client.patch(
        f"/api/v1/admin/tournaments/{tid}",
        json={"name": "Cup 2", "description": None},
        headers=_h(),
    )
    assert patched.status_code == 200 and patched.json()["name"] == "Cup 2"
    assert patched.json()["description"] is None
    assert (
        client.patch(f"/api/v1/admin/tournaments/{tid}", json={}, headers=_h()).status_code == 422
    )
    assert (
        client.patch(
            f"/api/v1/admin/tournaments/{tid}", json={"status": "completed"}, headers=_h()
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/admin/tournaments/{tid}", json={"name": None}, headers=_h()
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/admin/tournaments/{tid}", json={"status": "canceled"}, headers=_h()
        ).json()["status"]
        == "canceled"
    )
    assert (
        client.patch(
            f"/api/v1/admin/tournaments/{tid}", json={"status": "canceled"}, headers=_h()
        ).status_code
        == 409
    )
    assert (
        client.patch(
            "/api/v1/admin/tournaments/00000000-0000-0000-0000-000000000000",
            json={"name": "x"},
            headers=_h(),
        ).status_code
        == 404
    )
    listing = client.get("/api/v1/admin/tournaments", headers=_h())
    assert listing.status_code == 200 and len(listing.json()["items"]) == 1
    assert _actions(factory).count("tournament.update") == 2


def test_cancel_in_progress_keeps_rated_matches(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 4)
    tid = _tournament(client, players)
    _generate(client, tid)
    assert _play(client, tid, 1, 0, "a").status_code == 201
    rating = client.get(f"/api/v1/players/{players[0]}").json()["current_rating"]
    assert rating == 1516
    response = client.patch(
        f"/api/v1/admin/tournaments/{tid}", json={"status": "canceled"}, headers=_h()
    )
    assert response.status_code == 200 and response.json()["status"] == "canceled"
    assert client.get(f"/api/v1/players/{players[0]}").json()["current_rating"] == rating
    assert _play(client, tid, 1, 1, "a").status_code == 409


def test_audit_entries_for_every_tournament_write(api_client: ApiClient) -> None:
    client, factory = api_client
    players = _players(client, 2)
    tid = _tournament(client, players)
    client.patch(f"/api/v1/admin/tournaments/{tid}", json={"name": "Renamed"}, headers=_h())
    extra = client.post("/api/v1/admin/tournaments", json={"name": "Other"}, headers=_h()).json()[
        "id"
    ]
    client.post(
        f"/api/v1/admin/tournaments/{extra}/participants",
        json={"participants": [{"player_id": players[0]}]},
        headers=_h(),
    )
    client.delete(f"/api/v1/admin/tournaments/{extra}/participants/{players[0]}", headers=_h())
    _generate(client, tid)
    assert _play(client, tid, 1, 0).status_code == 201
    with factory() as db:
        rows = list(db.scalars(select(AuditLog).where(AuditLog.entity_type == "tournament")))
    by_action = {row.action: row for row in rows}
    assert {
        "tournament.create",
        "tournament.update",
        "tournament.participants_add",
        "tournament.participant_remove",
        "tournament.bracket_generate",
        "tournament.match_record",
    } <= set(by_action)
    assert all(row.actor_id == "dev-admin" for row in rows)
    assert by_action["tournament.update"].before_data["name"] == "Open"
    assert by_action["tournament.update"].after_data["name"] == "Renamed"
    assert by_action["tournament.match_record"].after_data["winner_id"]


def test_failed_record_rolls_back_everything(api_client: ApiClient) -> None:
    client, factory = api_client
    players = _players(client, 2)
    tid = _tournament(client, players)
    slot = _slot(_generate(client, tid), 1, 0)
    # Inactivating a participant after the draw makes the match service reject the result.
    client.patch(f"/api/v1/admin/players/{players[1]}", json={"is_active": False}, headers=_h())
    response = client.post(
        f"/api/v1/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": slot["id"],
            "winner_id": players[0],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    )
    assert response.status_code == 422
    assert _slot(_bracket(client, tid), 1, 0)["status"] == "ready"
    assert "tournament.match_record" not in _actions(factory)
    assert client.get("/api/v1/matches", params={"status": "all"}).json()["total"] == 0


ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/admin/tournaments", None),
    ("POST", "/admin/tournaments", {"name": "x"}),
    ("PATCH", "/admin/tournaments/00000000-0000-0000-0000-000000000000", {"name": "x"}),
    (
        "POST",
        "/admin/tournaments/00000000-0000-0000-0000-000000000000/participants",
        {"participants": []},
    ),
    (
        "DELETE",
        "/admin/tournaments/00000000-0000-0000-0000-000000000000/participants/00000000-0000-0000-0000-000000000000",
        None,
    ),
    ("POST", "/admin/tournaments/00000000-0000-0000-0000-000000000000/generate-bracket", {}),
    ("POST", "/admin/tournaments/00000000-0000-0000-0000-000000000000/matches", {}),
    ("GET", "/admin/achievements", None),
    ("POST", "/admin/achievements", {"name": "x", "description": "y"}),
    ("PATCH", "/admin/achievements/00000000-0000-0000-0000-000000000000", {"name": "x"}),
    ("GET", "/admin/player-achievements", None),
    ("POST", "/admin/players/00000000-0000-0000-0000-000000000000/achievements", {}),
    ("DELETE", "/admin/player-achievements/00000000-0000-0000-0000-000000000000", None),
]


@pytest.mark.parametrize(("method", "path", "body"), ROUTES)
def test_new_admin_routes_require_auth(
    api_client: ApiClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    client, _ = api_client
    send: Callable[..., Any] = client.request
    url = f"/api/v1{path}"
    anonymous = send(method, url, json=body)
    assert anonymous.status_code == 401
    bad = send(method, url, json=body, headers={"Authorization": "Bearer wrong"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthorized"


def test_match_response_includes_deleted_at(api_client: ApiClient) -> None:
    client, _ = api_client
    players = _players(client, 2)
    created = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": players[0],
            "player_b_id": players[1],
            "winner_id": players[0],
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=_h(),
    ).json()
    assert created["deleted_at"] is None
    assert client.get(f"/api/v1/matches/{created['id']}").json()["deleted_at"] is None
    assert client.get("/api/v1/matches").json()["items"][0]["deleted_at"] is None
    client.delete(f"/api/v1/admin/matches/{created['id']}", params={"reason": "void"}, headers=_h())
    assert client.get(f"/api/v1/matches/{created['id']}").status_code == 404
    listing = client.get(
        "/api/v1/admin/matches", params={"include_deleted": "true"}, headers=_h()
    ).json()
    assert listing["items"][0]["deleted_at"] is not None
    pm = client.get(f"/api/v1/players/{players[0]}/matches", params={"status": "all"}).json()
    assert pm["items"] == []


def test_participant_rows_unaffected_by_bye_slots(api_client: ApiClient) -> None:
    client, factory = api_client
    tid = _tournament(client, _players(client, 3))
    _generate(client, tid)
    with factory() as db:
        rows = list(db.scalars(select(TournamentParticipant)))
    assert sorted(row.seed for row in rows) == [1, 2, 3]
    assert all(row.final_position is None for row in rows)
