"""Independent QA of the tournament admin write API (docs/API.md, Admin -> Tournaments)."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.qa.api_helpers import (  # noqa: F401  (autouse fixture)
    API,
    audit_actions,
    auth,
    bracket,
    club_match,
    detail,
    generate,
    make_players,
    make_tournament,
    next_date,
    play_out,
    ratings,
    record,
    reset_auth_limiter,
    slot,
    slots,
)
from tests.qa.reference import elo_delta

ApiClient = tuple[TestClient, sessionmaker[Session]]


def _seed_positions(size: int) -> list[int]:
    """Independent standard seed placement: pairs sum to size + 1, 1 and 2 apart."""
    order = [1, 2]
    while len(order) < size:
        total = len(order) * 2 + 1
        nxt: list[int] = []
        for s in order:
            nxt += [s, total - s]
        order = nxt
    return order


@pytest.mark.parametrize("n,size", [(2, 2), (3, 4), (5, 8), (6, 8), (8, 8)])
def test_bracket_structure(api_client: ApiClient, n: int, size: int) -> None:
    client, _ = api_client
    tid = make_tournament(client, make_players(client, n))
    r = generate(client, tid)
    assert r.status_code == 200, r.text
    br = r.json()
    assert br["tournament_id"] == tid
    # rounds: log2(size); round r has size / 2**r matches
    assert [len(rnd["matches"]) for rnd in br["rounds"]] == [
        size // 2**k for k in range(1, size.bit_length())
    ]
    assert br["rounds"][-1]["name"] == "Final"
    first = br["rounds"][0]["matches"]
    byes = [m for m in first if m["is_bye"]]
    assert len(byes) == size - n
    seeds_with_bye = set()
    for m in byes:
        assert m["status"] == "bye"
        assert (m["player_a"] is None) != (m["player_b"] is None)
        winner = m["player_a"] or m["player_b"]
        assert m["winner_id"] == winner["id"]
        seeds_with_bye.add(m["seed_a"] if m["player_a"] else m["seed_b"])
    # byes go to the top seeds
    assert seeds_with_bye == set(range(1, size - n + 1))
    # seed placement matches the standard layout (independent computation)
    placed = []
    for m in first:
        placed += [m["seed_a"], m["seed_b"]]
    expected = [s if s <= n else None for s in _seed_positions(size)]
    assert placed == expected
    # seeds 1 and 2 on opposite halves
    if size > 2:
        half = size // 2
        assert (placed.index(1) < half) != (placed.index(2) < half)
    # byes auto-advanced into round 2
    if size > 2:
        r2_players = {
            p["id"] for m in br["rounds"][1]["matches"] for p in (m["player_a"], m["player_b"]) if p
        }
        assert {(m["player_a"] or m["player_b"])["id"] for m in byes} <= r2_players
    # real first-round matches are ready, later non-bye matches with a gap are pending
    for m in first:
        if not m["is_bye"]:
            assert m["status"] == "ready"
    d = detail(client, tid)
    assert d["status"] == "in_progress"
    assert sorted(p["seed"] for p in d["participants"]) == list(range(1, n + 1))


def test_rating_seeding_orders_by_rating(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    club_match(client, p[2], p[3], p[2])  # Q3 up, Q4 down
    club_match(client, p[2], p[0], p[2])
    r = ratings(client)
    tid = make_tournament(client, p)
    assert generate(client, tid, seeding="rating").status_code == 200
    d = detail(client, tid)
    by_seed = sorted(d["participants"], key=lambda x: x["seed"])
    assert [x["seed"] for x in by_seed] == [1, 2, 3, 4]
    rs = [r[x["player"]["id"]] for x in by_seed]
    assert rs == sorted(rs, reverse=True)
    assert by_seed[0]["player"]["id"] == p[2]


def test_manual_seeding_unseeded_last_by_rating(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 5)
    club_match(client, p[2], p[3], p[2])  # Q3 1516, Q4 1484
    club_match(client, p[2], p[4], p[2])  # Q3 1531ish, Q5 down; Q1, Q2 stay 1500
    r = ratings(client)
    tid = client.post(f"{API}/admin/tournaments", json={"name": "M"}, headers=auth()).json()["id"]
    body = {
        "participants": [
            {"player_id": p[3], "seed": 1},
            {"player_id": p[0], "seed": 2},
            {"player_id": p[2]},
            {"player_id": p[1]},
            {"player_id": p[4]},
        ]
    }
    assert (
        client.post(
            f"{API}/admin/tournaments/{tid}/participants", json=body, headers=auth()
        ).status_code
        == 200
    )
    assert generate(client, tid, seeding="manual").status_code == 200
    seeds = {x["player"]["id"]: x["seed"] for x in detail(client, tid)["participants"]}
    assert seeds[p[3]] == 1 and seeds[p[0]] == 2
    assert seeds[p[2]] == 3  # highest rated unseeded
    assert sorted(seeds.values()) == [1, 2, 3, 4, 5]
    assert r[p[1]] >= r[p[4]]
    assert seeds[p[1]] < seeds[p[4]]
    br = bracket(client, tid)
    first = br["rounds"][0]["matches"]
    # seed 1 on a bye, in slot 0
    assert first[0]["seed_a"] == 1 and first[0]["is_bye"]


def test_generate_requires_two_participants_and_valid_state(api_client: ApiClient) -> None:
    client, _ = api_client
    tid = make_tournament(client, make_players(client, 1))
    assert generate(client, tid).status_code == 422
    missing = generate(client, str(uuid.uuid4()))
    assert missing.status_code == 404
    assert generate(client, tid, seeding="bogus").status_code == 422


def test_recording_rejections_and_advancement(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p)
    # draft tournament: 409
    other = make_tournament(client, make_players(client, 2, "Z"), "Other")
    br_other = generate(client, other).json()
    draft = make_tournament(client, None, "Draft")
    bogus = {
        "bracket_match_id": slot(br_other, 1, 0)["id"],
        "winner_id": p[0],
        "match_date": next_date(),
    }
    assert (
        client.post(
            f"{API}/admin/tournaments/{draft}/matches", json=bogus, headers=auth()
        ).status_code
        == 409
    )
    br = generate(client, tid).json()
    final = slot(br, 2, 0)
    assert final["status"] == "pending"
    # pending match: 422
    assert record(client, tid, final, p[0]).status_code == 422
    # bracket match from another tournament: 404
    r = client.post(f"{API}/admin/tournaments/{tid}/matches", json=bogus, headers=auth())
    assert r.status_code == 404
    sf = slot(br, 1, 0)
    # winner not in the match
    outsider = slot(br, 1, 1)["player_a"]["id"]
    assert record(client, tid, sf, outsider).status_code == 422
    assert detail(client, tid)["status"] == "in_progress"
    assert all(m["match_id"] is None for m in slots(bracket(client, tid)))
    # valid
    winner = sf["player_b"]["id"]
    ok = record(client, tid, sf, winner)
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert set(body) == {"match", "bracket"}
    assert body["match"]["tournament"]["id"] == tid
    assert body["match"]["winner_id"] == winner
    done = slot(body["bracket"], 1, 0)
    assert done["status"] == "completed" and done["winner_id"] == winner
    assert done["match_id"] == body["match"]["id"]
    nxt = slot(body["bracket"], 2, 0)
    assert winner in {
        nxt["player_a"]["id"] if nxt["player_a"] else None,
        nxt["player_b"]["id"] if nxt["player_b"] else None,
    }
    assert nxt["status"] == "pending"
    # re-recording a completed bracket match is rejected, no second rated match
    again = record(client, tid, sf, winner)
    assert again.status_code == 422
    n_matches = client.get(f"{API}/matches", params={"page_size": 100}).json()["total"]
    assert n_matches == 1
    # a bye match cannot be recorded
    five = make_tournament(client, make_players(client, 3, "B"), "Byes")
    bb = generate(client, five).json()
    bye = slot(bb, 1, 0)
    assert bye["is_bye"]
    assert record(client, five, bye, (bye["player_a"] or bye["player_b"])["id"]).status_code == 422


@pytest.mark.parametrize(
    "n,expected",
    [
        (2, [1, 2]),
        (3, [1, 2, 3]),
        (4, [1, 2, 3, 3]),
        (5, [1, 2, 3, 3, 5]),
        (6, [1, 2, 3, 3, 5, 5]),
        (8, [1, 2, 3, 3, 5, 5, 5, 5]),
    ],
)
def test_final_completes_with_positions(api_client: ApiClient, n: int, expected: list[int]) -> None:
    client, _ = api_client
    p = make_players(client, n)
    tid = make_tournament(client, p)
    generate(client, tid)
    play_out(client, tid)
    d = detail(client, tid)
    assert d["status"] == "completed"
    assert sorted(x["final_position"] for x in d["participants"]) == expected
    final = slots(bracket(client, tid))[-1]
    champ = next(x for x in d["participants"] if x["final_position"] == 1)
    assert d["champion"]["id"] == champ["player"]["id"] == final["winner_id"]
    assert (
        d["runner_up"]["id"]
        == next(x for x in d["participants"] if x["final_position"] == 2)["player"]["id"]
    )
    assert sum(ratings(client).values()) == 1500 * n


def test_tournament_elo_matches_club_formula_and_zero_sum(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 8)
    # spread ratings so the Elo expectation is not trivial
    club_match(client, p[0], p[1], p[0])
    club_match(client, p[0], p[2], p[0])
    club_match(client, p[3], p[4], p[3])
    tid = make_tournament(client, p)
    generate(client, tid)
    while True:
        ready = [m for m in slots(bracket(client, tid)) if m["status"] == "ready"]
        if not ready:
            break
        m = ready[0]
        before = ratings(client)
        a, b = m["player_a"]["id"], m["player_b"]["id"]
        # let the lower-rated player win when possible, to exercise upsets
        win, lose = (a, b) if before[a] <= before[b] else (b, a)
        r = record(client, tid, m, win)
        assert r.status_code == 201, r.text
        delta = elo_delta(before[win], before[lose])
        changes = {c["player_id"]: c for c in r.json()["match"]["rating_changes"]}
        assert changes[win]["rating_change"] == delta
        assert changes[lose]["rating_change"] == -delta
        assert changes[win]["old_rating"] == before[win]
        after = ratings(client)
        assert after[win] == before[win] + delta and after[lose] == before[lose] - delta
        assert sum(after.values()) == 1500 * 8
    # a club match with the same rating gap gives the same delta
    before = ratings(client)
    x, y = p[5], p[6]
    res = club_match(client, x, y, x)
    expected = elo_delta(before[x], before[y])
    assert {c["player_id"]: c["rating_change"] for c in res["rating_changes"]}[x] == expected


def test_regeneration_only_before_any_result(api_client: ApiClient) -> None:
    client, _ = api_client
    tid = make_tournament(client, make_players(client, 4))
    first = generate(client, tid)
    assert first.status_code == 200
    second = generate(client, tid, seeding="rating")
    assert second.status_code == 200
    assert len(slots(second.json())) == 3
    assert record(client, tid, slot(second.json(), 1, 0)).status_code == 201
    third = generate(client, tid)
    assert third.status_code == 409
    after = bracket(client, tid)
    assert slot(after, 1, 0)["status"] == "completed"
    # completed and canceled tournaments cannot be regenerated either
    play_out(client, tid)
    assert detail(client, tid)["status"] == "completed"
    assert generate(client, tid).status_code == 409
    c = make_tournament(client, make_players(client, 2, "C"), "C")
    assert (
        client.patch(
            f"{API}/admin/tournaments/{c}", json={"status": "canceled"}, headers=auth()
        ).status_code
        == 200
    )
    assert generate(client, c).status_code == 409


def test_participants_only_in_draft(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p[:2])
    url = f"{API}/admin/tournaments/{tid}/participants"
    dup = client.post(url, json={"participants": [{"player_id": p[0]}]}, headers=auth())
    assert dup.status_code == 409
    unknown = client.post(
        url, json={"participants": [{"player_id": str(uuid.uuid4())}]}, headers=auth()
    )
    assert unknown.status_code == 422
    assert client.delete(f"{API}/admin/players/{p[2]}", headers=auth()).status_code == 200
    inactive = client.post(url, json={"participants": [{"player_id": p[2]}]}, headers=auth())
    assert inactive.status_code == 422
    assert detail(client, tid)["participant_count"] == 2
    added = client.post(url, json={"participants": [{"player_id": p[3]}]}, headers=auth())
    assert added.status_code == 200
    assert added.json()["participant_count"] == 3
    removed = client.delete(f"{url}/{p[3]}", headers=auth())
    assert removed.status_code == 200 and removed.json()["participant_count"] == 2
    assert client.delete(f"{url}/{p[3]}", headers=auth()).status_code in (404, 422)
    generate(client, tid)
    assert (
        client.post(url, json={"participants": [{"player_id": p[3]}]}, headers=auth()).status_code
        == 409
    )
    assert client.delete(f"{url}/{p[0]}", headers=auth()).status_code == 409
    assert detail(client, tid)["participant_count"] == 2


def _state(client: TestClient, tid: str) -> tuple[Any, Any, Any]:
    return (
        ratings(client),
        bracket(client, tid),
        sorted(
            (x["player"]["id"], x["final_position"]) for x in detail(client, tid)["participants"]
        ),
    )


def _mutations(mid: str) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        ("POST", f"{API}/admin/matches/{mid}/cancel", {"json": {"reason": "qa"}}),
        ("DELETE", f"{API}/admin/matches/{mid}", {"params": {"reason": "qa"}}),
        (
            "POST",
            f"{API}/admin/matches/{mid}/correct",
            {"json": {"status": "disputed", "reason": "qa"}},
        ),
    ]


@pytest.mark.parametrize("which", [0, 1, 2])
def test_mutating_match_with_decided_next_round_is_rejected_without_side_effects(
    api_client: ApiClient, which: int
) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p)
    br = generate(client, tid).json()
    first = record(client, tid, slot(br, 1, 0)).json()["match"]
    record(client, tid, slot(bracket(client, tid), 1, 1))
    record(client, tid, slot(bracket(client, tid), 2, 0))  # final decided -> tournament completed
    assert detail(client, tid)["status"] == "completed"
    before = _state(client, tid)
    audit_before = len(audit_actions(client, "match.cancel")) + len(
        audit_actions(client, "match.delete")
    )
    method, url, kw = _mutations(first["id"])[which]
    r = client.request(method, url, headers=auth(), **kw)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "business_rule_violation"
    assert _state(client, tid) == before
    assert detail(client, tid)["status"] == "completed"
    assert client.get(f"{API}/matches/{first['id']}").json()["status"] == "completed"
    assert audit_before == len(audit_actions(client, "match.cancel")) + len(
        audit_actions(client, "match.delete")
    )
    # a winner change is rejected too
    loser = (
        first["player_a"]["id"]
        if first["winner_id"] != first["player_a"]["id"]
        else first["player_b"]["id"]
    )
    r2 = client.post(
        f"{API}/admin/matches/{first['id']}/correct",
        json={"winner_id": loser, "reason": "qa"},
        headers=auth(),
    )
    assert r2.status_code == 422
    assert _state(client, tid) == before


@pytest.mark.parametrize("which", [0, 1, 2])
def test_mutating_undecided_tournament_match_reopens_slot(
    api_client: ApiClient, which: int
) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p)
    br = generate(client, tid).json()
    sf = slot(br, 1, 0)
    first = record(client, tid, sf).json()["match"]
    assert ratings(client)[first["winner_id"]] == 1516
    method, url, kw = _mutations(first["id"])[which]
    r = client.request(method, url, headers=auth(), **kw)
    assert r.status_code == 200, r.text
    after = bracket(client, tid)
    reopened = slot(after, 1, 0)
    assert reopened["status"] == "ready"
    assert reopened["winner_id"] is None and reopened["match_id"] is None
    nxt = slot(after, 2, 0)
    assert nxt["player_a"] is None and nxt["player_b"] is None
    assert set(ratings(client).values()) == {1500}
    # the slot can be played again
    again = record(client, tid, reopened, reopened["player_b"]["id"])
    assert again.status_code == 201
    assert detail(client, tid)["status"] == "in_progress"


def test_reopening_final_reopens_completed_tournament(api_client: ApiClient) -> None:
    client, _ = api_client
    tid = make_tournament(client, make_players(client, 2))
    br = generate(client, tid).json()
    m = record(client, tid, slot(br, 1, 0)).json()["match"]
    assert detail(client, tid)["status"] == "completed"
    r = client.post(f"{API}/admin/matches/{m['id']}/cancel", json={"reason": "qa"}, headers=auth())
    assert r.status_code == 200
    d = detail(client, tid)
    assert d["status"] == "in_progress"
    assert all(x["final_position"] is None for x in d["participants"])
    assert d["champion"] is None
    assert slot(bracket(client, tid), 1, 0)["status"] == "ready"


def test_correct_winner_updates_advancement_when_next_undecided(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p)
    br = generate(client, tid).json()
    sf = slot(br, 1, 0)
    m = record(client, tid, sf, sf["player_a"]["id"]).json()["match"]
    new_winner = sf["player_b"]["id"]
    r = client.post(
        f"{API}/admin/matches/{m['id']}/correct",
        json={"winner_id": new_winner, "reason": "qa"},
        headers=auth(),
    )
    assert r.status_code == 200, r.text
    after = bracket(client, tid)
    assert slot(after, 1, 0)["winner_id"] == new_winner
    nxt = slot(after, 2, 0)
    ids = {x["id"] for x in (nxt["player_a"], nxt["player_b"]) if x}
    assert ids == {new_winner}
    # players of a tournament match cannot be changed
    other = next(x for x in p if x not in (sf["player_a"]["id"], sf["player_b"]["id"]))
    bad = client.post(
        f"{API}/admin/matches/{m['id']}/correct",
        json={"player_b_id": other, "winner_id": sf["player_a"]["id"], "reason": "qa"},
        headers=auth(),
    )
    assert bad.status_code == 422
    # club endpoint cannot create tournament matches
    assert (
        client.post(
            f"{API}/admin/matches",
            json={
                "player_a_id": p[0],
                "player_b_id": p[1],
                "winner_id": p[0],
                "match_date": next_date(),
                "tournament_id": tid,
            },
            headers=auth(),
        ).status_code
        == 422
    )


def test_cancel_tournament_keeps_matches_rated(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 4)
    tid = make_tournament(client, p)
    br = generate(client, tid).json()
    m = record(client, tid, slot(br, 1, 0)).json()["match"]
    before = ratings(client)
    assert sorted(before.values()) == [1484, 1500, 1500, 1516]
    r = client.patch(f"{API}/admin/tournaments/{tid}", json={"status": "canceled"}, headers=auth())
    assert r.status_code == 200 and r.json()["status"] == "canceled"
    assert ratings(client) == before
    got = client.get(f"{API}/matches/{m['id']}").json()
    assert got["status"] == "completed" and got["tournament"]["id"] == tid
    assert got["rating_changes"]
    # no more results on a canceled tournament
    nxt = slot(bracket(client, tid), 1, 1)
    assert record(client, tid, nxt).status_code == 409
    # draft can be canceled too; only "canceled" is accepted as a status
    d = make_tournament(client, None, "D")
    assert (
        client.patch(
            f"{API}/admin/tournaments/{d}", json={"status": "completed"}, headers=auth()
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"{API}/admin/tournaments/{d}", json={"status": "canceled"}, headers=auth()
        ).status_code
        == 200
    )


def test_create_and_update_validation(api_client: ApiClient) -> None:
    client, _ = api_client
    assert (
        client.post(f"{API}/admin/tournaments", json={"name": ""}, headers=auth()).status_code
        == 422
    )
    assert (
        client.post(
            f"{API}/admin/tournaments", json={"name": "x" * 101}, headers=auth()
        ).status_code
        == 422
    )
    r = client.post(
        f"{API}/admin/tournaments",
        json={
            "name": "Cup",
            "description": "d",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
        },
        headers=auth(),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "draft" and body["participant_count"] == 0
    assert body["start_date"] == "2026-12-01" and body["bracket_generated"] is False
    u = client.patch(
        f"{API}/admin/tournaments/{body['id']}", json={"name": "Cup 2"}, headers=auth()
    )
    assert u.status_code == 200 and u.json()["name"] == "Cup 2"
    assert (
        client.patch(
            f"{API}/admin/tournaments/{uuid.uuid4()}", json={"name": "x"}, headers=auth()
        ).status_code
        == 404
    )
    listed = client.get(f"{API}/admin/tournaments", headers=auth())
    assert listed.status_code == 200 and len(listed.json()["items"]) == 1


def test_audit_action_names(api_client: ApiClient) -> None:
    client, _ = api_client
    p = make_players(client, 3)
    tid = make_tournament(client, p[:2])
    client.patch(f"{API}/admin/tournaments/{tid}", json={"description": "x"}, headers=auth())
    client.post(
        f"{API}/admin/tournaments/{tid}/participants",
        json={"participants": [{"player_id": p[2]}]},
        headers=auth(),
    )
    client.delete(f"{API}/admin/tournaments/{tid}/participants/{p[2]}", headers=auth())
    br = generate(client, tid).json()
    record(client, tid, slot(br, 1, 0))
    for action, n in [
        ("tournament.create", 1),
        ("tournament.update", 1),
        ("tournament.participants_add", 2),  # initial add + p[2]
        ("tournament.participant_remove", 1),
        ("tournament.bracket_generate", 1),
        ("tournament.match_record", 1),
        ("match.create", 1),
    ]:
        entries = audit_actions(client, action)
        assert len(entries) == n, (action, len(entries))
        assert all(e["actor_id"] for e in entries)
    entry = audit_actions(client, "tournament.match_record")[0]
    assert entry["entity_type"] and entry["entity_id"]
    assert entry["after_data"] is not None


def _routes() -> list[tuple[str, str, dict[str, Any]]]:
    t, p, bm = (str(uuid.uuid4()) for _ in range(3))
    return [
        ("GET", "/admin/tournaments", {}),
        ("POST", "/admin/tournaments", {"json": {"name": "N"}}),
        ("PATCH", f"/admin/tournaments/{t}", {"json": {"name": "N"}}),
        (
            "POST",
            f"/admin/tournaments/{t}/participants",
            {"json": {"participants": [{"player_id": p}]}},
        ),
        ("DELETE", f"/admin/tournaments/{t}/participants/{p}", {}),
        ("POST", f"/admin/tournaments/{t}/generate-bracket", {"json": {}}),
        (
            "POST",
            f"/admin/tournaments/{t}/matches",
            {
                "json": {
                    "bracket_match_id": bm,
                    "winner_id": p,
                    "match_date": "2026-10-01T10:00:00Z",
                }
            },
        ),
        ("GET", "/admin/achievements", {}),
        ("POST", "/admin/achievements", {"json": {"name": "N", "description": "d"}}),
        ("PATCH", f"/admin/achievements/{t}", {"json": {"name": "N"}}),
        ("GET", "/admin/player-achievements", {}),
        ("POST", f"/admin/players/{p}/achievements", {"json": {"achievement_id": t}}),
        ("DELETE", f"/admin/player-achievements/{t}", {}),
    ]


@pytest.mark.parametrize("header", [None, "Bearer wrong-token", "Bearer ", "Basic abc", "garbage"])
def test_new_admin_routes_reject_unauthenticated(api_client: ApiClient, header: str | None) -> None:
    client, _ = api_client
    headers = {"Authorization": header} if header is not None else {}
    for method, path, kw in _routes():
        r = client.request(method, API + path, headers=headers, **kw)
        assert r.status_code == 401, (method, path, r.status_code)
        assert r.json()["error"]["code"] == "unauthorized"
    # nothing was created
    assert client.get(f"{API}/tournaments").json()["items"] == []
    assert client.get(f"{API}/achievements").json()["items"] == []
