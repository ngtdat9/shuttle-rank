"""Public read endpoints: status codes, shapes, filters, and pagination."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.services.match_service import delete_match
from app.services.player_service import deactivate_player
from tests.factories import (
    add_bracket_slot,
    add_participant,
    award,
    make_achievement,
    make_match,
    make_player,
    make_tournament,
)


def _seed(factory: sessionmaker[Session]) -> dict[str, str]:
    db = factory()
    try:
        amy = make_player(db, "Amy")
        bob = make_player(db, "Bob")
        cara = make_player(db, "Cara")
        gina = make_player(db, "Gina")
        deactivate_player(db, gina.id, actor="tester")
        now = datetime.now(UTC)
        older = now - timedelta(days=40)
        middle = now - timedelta(days=10)
        city = make_tournament(db, "City Open", status="in_progress", start_date=now.date())
        winter = make_tournament(
            db, "Winter Cup", status="draft", start_date=(now - timedelta(days=20)).date()
        )
        spring = make_tournament(
            db,
            "Spring Cup",
            status="completed",
            start_date=(now - timedelta(days=80)).date(),
        )
        add_participant(db, city, amy, seed=1)
        add_participant(db, city, bob, seed=2)
        add_participant(db, spring, amy, seed=1, final_position=1)
        add_participant(db, spring, bob, seed=2, final_position=2)
        first = make_match(
            db,
            amy,
            bob,
            winner=amy,
            match_date=older,
            game_scores=[[21, 18]],
            notes="opener",
        )
        second = make_match(db, bob, cara, winner=bob, match_date=middle)
        third = make_match(
            db,
            amy,
            bob,
            winner=bob,
            match_date=now,
            tournament_id=city.id,
            game_scores=[[21, 19]],
        )
        canceled = make_match(db, amy, cara, status="canceled", match_date=middle)
        make_match(db, bob, cara, status="disputed", match_date=middle)
        removed = make_match(db, amy, cara, winner=cara, match_date=older)
        delete_match(db, removed.id, "duplicate", "tester")
        add_bracket_slot(db, city, round_number=1, position=0, player_a=amy, player_b=bob)
        add_bracket_slot(
            db,
            city,
            round_number=1,
            position=1,
            player_a=amy,
            winner=amy,
            is_bye=True,
        )
        add_bracket_slot(db, city, round_number=2, position=0, player_a=amy)
        linked = add_bracket_slot(
            db,
            city,
            round_number=2,
            position=1,
            player_a=amy,
            player_b=bob,
            winner=bob,
            match=third,
        )
        iron = make_achievement(db, "Iron Will", description="Never retired")
        make_achievement(db, "Old Trophy", is_active=False)
        award(db, amy, iron, notes="season opener", awarded_at=now - timedelta(days=1))
        return {
            "amy": str(amy.id),
            "bob": str(bob.id),
            "cara": str(cara.id),
            "gina": str(gina.id),
            "first": str(first.id),
            "second": str(second.id),
            "third": str(third.id),
            "canceled": str(canceled.id),
            "removed": str(removed.id),
            "city": str(city.id),
            "winter": str(winter.id),
            "spring": str(spring.id),
            "linked_slot": str(linked.id),
            "older": older.date().isoformat(),
        }
    finally:
        db.close()


def test_empty_reads(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _factory = api_client
    rankings = client.get("/api/v1/rankings")
    assert rankings.status_code == 200
    assert rankings.json() == {"items": [], "last_updated": None}
    monthly = client.get("/api/v1/rankings/monthly")
    assert monthly.status_code == 200
    assert monthly.json() == {
        "available_months": [],
        "year": None,
        "month": None,
        "items": [],
    }
    dashboard = client.get("/api/v1/dashboard")
    body = dashboard.json()
    assert dashboard.status_code == 200
    assert body["leader"] is None
    assert body["top_players"] == []
    assert body["totals"] == {
        "active_players": 0,
        "total_matches": 0,
        "matches_this_month": 0,
        "tournaments_completed": 0,
    }
    assert body["last_updated"] is None


def test_public_endpoints(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api_client
    ids = _seed(factory)

    rankings = client.get("/api/v1/rankings")
    assert rankings.status_code == 200
    board = rankings.json()
    assert [row["player"]["display_name"] for row in board["items"]] == ["Bob", "Amy", "Cara"]
    assert "Gina" not in {row["player"]["display_name"] for row in board["items"]}
    assert board["last_updated"] is not None
    included = client.get("/api/v1/rankings", params={"include_inactive": True})
    assert any(row["player"]["display_name"] == "Gina" for row in included.json()["items"])
    by_wins = client.get("/api/v1/rankings", params={"sort": "wins", "order": "desc"})
    assert by_wins.status_code == 200
    assert by_wins.json()["items"][0]["wins"] >= by_wins.json()["items"][-1]["wins"]

    players = client.get("/api/v1/players", params={"search": "amy"})
    assert players.status_code == 200
    assert [item["display_name"] for item in players.json()["items"]] == ["Amy"]
    assert players.json()["items"][0]["rank"] == board["items"][1]["rank"]
    inactive = client.get("/api/v1/players", params={"include_inactive": True, "search": "gina"})
    assert inactive.json()["items"][0]["rank"] is None
    assert inactive.json()["items"][0]["is_active"] is False

    profile = client.get(f"/api/v1/players/{ids['amy']}")
    assert profile.status_code == 200
    body = profile.json()
    assert body["display_name"] == "Amy"
    assert body["stats"]["matches_played"] == 2
    assert body["stats"]["recent_form"][0] in {"W", "L"}
    assert "created_at" in body
    missing_player = client.get(f"/api/v1/players/{uuid.uuid4()}")
    assert missing_player.status_code == 404
    assert missing_player.json()["error"]["code"] == "not_found"

    history = client.get(f"/api/v1/players/{ids['amy']}/rating-history")
    assert history.status_code == 200
    points = history.json()
    assert points["starting_rating"] == 1500
    assert [point["old_rating"] for point in points["points"]][0] == 1500
    assert points["points"][0]["match_date"] <= points["points"][-1]["match_date"]
    assert {"opponent", "result", "rating_change"} <= set(points["points"][0])

    player_matches = client.get(
        f"/api/v1/players/{ids['amy']}/matches",
        params={"page": 1, "page_size": 1},
    )
    assert player_matches.status_code == 200
    page = player_matches.json()
    assert page["total"] == 2
    assert page["page"] == 1
    assert page["page_size"] == 1
    assert len(page["items"]) == 1
    assert page["items"][0]["opponent"]["id"] == ids["bob"]
    assert page["items"][0]["result"] in {"W", "L"}
    all_statuses = client.get(
        f"/api/v1/players/{ids['amy']}/matches",
        params={"status": "all", "page_size": 50},
    )
    statuses = {item["status"] for item in all_statuses.json()["items"]}
    assert "canceled" in statuses
    assert ids["removed"] not in {item["id"] for item in all_statuses.json()["items"]}

    monthly = client.get(f"/api/v1/players/{ids['amy']}/monthly")
    assert monthly.status_code == 200
    assert monthly.json()["items"]
    assert monthly.json()["items"][0]["rating"] == 1516

    achievements = client.get(f"/api/v1/players/{ids['amy']}/achievements")
    assert achievements.status_code == 200
    assert achievements.json()["items"][0]["notes"] == "season opener"
    assert achievements.json()["items"][0]["achievement"]["awarded_count"] == 1

    matches = client.get("/api/v1/matches", params={"page_size": 1})
    assert matches.status_code == 200
    listed = matches.json()
    assert listed["total"] == 3
    assert len(listed["items"]) == 1
    second_page = client.get("/api/v1/matches", params={"page": 2, "page_size": 1})
    assert second_page.json()["items"][0]["id"] != listed["items"][0]["id"]
    searched = client.get("/api/v1/matches", params={"search": "amy", "page_size": 20})
    assert {item["id"] for item in searched.json()["items"]} == {ids["first"], ids["third"]}
    dated = client.get(
        "/api/v1/matches",
        params={"date_from": ids["older"], "date_to": ids["older"]},
    )
    assert [item["id"] for item in dated.json()["items"]] == [ids["first"]]
    by_player = client.get("/api/v1/matches", params={"player_id": ids["cara"]})
    assert [item["id"] for item in by_player.json()["items"]] == [ids["second"]]
    by_tournament = client.get("/api/v1/matches", params={"tournament_id": ids["city"]})
    assert [item["id"] for item in by_tournament.json()["items"]] == [ids["third"]]
    canceled = client.get("/api/v1/matches", params={"status": "canceled"})
    assert [item["id"] for item in canceled.json()["items"]] == [ids["canceled"]]
    everything = client.get("/api/v1/matches", params={"status": "all", "page_size": 50})
    assert everything.json()["total"] == 5
    assert ids["removed"] not in {item["id"] for item in everything.json()["items"]}

    detail = client.get(f"/api/v1/matches/{ids['first']}")
    assert detail.status_code == 200
    match_body = detail.json()
    assert match_body["game_scores"] == [[21, 18]]
    assert match_body["notes"] == "opener"
    assert match_body["player_a"]["display_name"] == "Amy"
    assert sum(change["rating_change"] for change in match_body["rating_changes"]) == 0
    assert client.get(f"/api/v1/matches/{ids['removed']}").status_code == 404
    assert client.get(f"/api/v1/matches/{uuid.uuid4()}").status_code == 404

    same = client.get(f"/api/v1/head-to-head/{ids['amy']}/{ids['amy']}")
    assert same.status_code == 422
    assert same.json()["error"]["code"] == "business_rule_violation"
    unknown = client.get(f"/api/v1/head-to-head/{ids['amy']}/{uuid.uuid4()}")
    assert unknown.status_code == 404
    paired = client.get(f"/api/v1/head-to-head/{ids['amy']}/{ids['bob']}")
    assert paired.status_code == 200
    assert paired.json()["total_matches"] == 2
    assert paired.json()["player_a_wins"] == 1
    assert paired.json()["player_b_wins"] == 1

    tournaments = client.get("/api/v1/tournaments")
    assert [item["name"] for item in tournaments.json()["items"]] == [
        "City Open",
        "Winter Cup",
        "Spring Cup",
    ]
    assert tournaments.json()["items"][0]["status"] == "in_progress"
    drafts = client.get("/api/v1/tournaments", params={"status": "draft"})
    assert [item["name"] for item in drafts.json()["items"]] == ["Winter Cup"]
    spring = client.get(f"/api/v1/tournaments/{ids['spring']}")
    assert spring.status_code == 200
    assert spring.json()["champion"]["display_name"] == "Amy"
    assert spring.json()["runner_up"]["display_name"] == "Bob"
    assert spring.json()["bracket_generated"] is False
    assert [row["seed"] for row in spring.json()["participants"]] == [1, 2]
    assert client.get(f"/api/v1/tournaments/{uuid.uuid4()}").status_code == 404

    bracket = client.get(f"/api/v1/tournaments/{ids['city']}/bracket")
    assert bracket.status_code == 200
    rounds = bracket.json()["rounds"]
    assert [round_["name"] for round_ in rounds] == ["Semifinals", "Final"]
    semifinal = rounds[0]["matches"]
    assert semifinal[0]["status"] == "ready"
    assert semifinal[1]["status"] == "bye"
    assert semifinal[1]["seed_a"] == 1
    final = rounds[1]["matches"]
    assert final[0]["status"] == "pending"
    assert final[1]["status"] == "completed"
    assert final[1]["match_id"] == ids["third"]
    assert final[1]["game_scores"] == [[21, 19]]
    assert client.get(f"/api/v1/tournaments/{uuid.uuid4()}/bracket").status_code == 404
    empty_bracket = client.get(f"/api/v1/tournaments/{ids['winter']}/bracket")
    assert empty_bracket.json()["rounds"] == []

    catalog = client.get("/api/v1/achievements")
    assert [item["name"] for item in catalog.json()["items"]] == ["Iron Will"]
    assert catalog.json()["items"][0]["awarded_count"] == 1
    with_inactive = client.get("/api/v1/achievements", params={"include_inactive": True})
    assert {item["name"] for item in with_inactive.json()["items"]} == {"Iron Will", "Old Trophy"}

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    home = dashboard.json()
    assert home["leader"]["player"]["display_name"] == "Bob"
    assert home["totals"]["active_players"] == 3
    assert home["totals"]["total_matches"] == 3
    assert home["totals"]["matches_this_month"] >= 1
    assert home["totals"]["tournaments_completed"] == 1
    assert home["recent_matches"][0]["id"] == ids["third"]
    assert home["rating_progression"][0]["points"][0] == {"match_date": None, "rating": 1500}
    assert home["active_tournament"]["name"] == "City Open"
    assert home["recent_achievements"][0]["player"]["display_name"] == "Amy"
    assert home["last_updated"] is not None

    month_board = client.get("/api/v1/rankings/monthly")
    assert month_board.status_code == 200
    assert month_board.json()["items"]
    missing_month = client.get("/api/v1/rankings/monthly", params={"year": 1999, "month": 1})
    assert missing_month.status_code == 404
    assert missing_month.json()["error"]["code"] == "not_found"

    assert client.get("/api/v1/rankings", params={"sort": "nope"}).status_code == 422
    assert (
        client.get("/api/v1/matches", params={"page": 0}).json()["error"]["code"]
        == "validation_error"
    )
    assert client.get("/api/v1/matches", params={"page_size": 101}).status_code == 422

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    for path in (
        "/api/v1/dashboard",
        "/api/v1/rankings",
        "/api/v1/rankings/monthly",
        "/api/v1/players",
        "/api/v1/players/{player_id}",
        "/api/v1/players/{player_id}/matches",
        "/api/v1/players/{player_id}/rating-history",
        "/api/v1/players/{player_id}/monthly",
        "/api/v1/players/{player_id}/achievements",
        "/api/v1/matches",
        "/api/v1/matches/{match_id}",
        "/api/v1/head-to-head/{player_a}/{player_b}",
        "/api/v1/tournaments",
        "/api/v1/tournaments/{tournament_id}",
        "/api/v1/tournaments/{tournament_id}/bracket",
        "/api/v1/achievements",
    ):
        assert path in paths
