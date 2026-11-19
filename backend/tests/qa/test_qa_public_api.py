"""Public API contract, filters, rankings, head-to-head, and dashboard checks."""

import re
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.factories import (
    add_bracket_slot,
    add_participant,
    award,
    make_achievement,
    make_match,
    make_player,
    make_tournament,
)
from tests.qa.reference import elo_delta

API = "/api/v1"
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Spec:
    def check(self, value: object, path: str) -> None:
        raise NotImplementedError


class Obj(Spec):
    def __init__(self, **fields: Spec) -> None:
        self.fields = fields

    def check(self, value: object, path: str) -> None:
        assert isinstance(value, dict), f"{path} expected object, got {type(value).__name__}"
        extra = set(value) - set(self.fields)
        missing = set(self.fields) - set(value)
        assert not extra and not missing, f"{path} extra={sorted(extra)} missing={sorted(missing)}"
        for key, spec in self.fields.items():
            spec.check(value[key], f"{path}.{key}")


class Arr(Spec):
    def __init__(self, item: Spec) -> None:
        self.item = item

    def check(self, value: object, path: str) -> None:
        assert isinstance(value, list), f"{path} expected list"
        for index, entry in enumerate(value):
            self.item.check(entry, f"{path}[{index}]")


class Opt(Spec):
    def __init__(self, inner: Spec) -> None:
        self.inner = inner

    def check(self, value: object, path: str) -> None:
        if value is not None:
            self.inner.check(value, path)


class Int(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, int) and not isinstance(value, bool), f"{path} expected int"


class Num(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{path} expected number"
        )


class Bool(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, bool), f"{path} expected bool"


class Text(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, str), f"{path} expected string"


class Exact(Spec):
    def __init__(self, expected: object) -> None:
        self.expected = expected

    def check(self, value: object, path: str) -> None:
        assert value == self.expected, f"{path} expected {self.expected!r}, got {value!r}"


class Lit(Spec):
    def __init__(self, *options: object) -> None:
        self.options = options

    def check(self, value: object, path: str) -> None:
        assert value in self.options, f"{path} expected one of {self.options}, got {value!r}"


class Uuid(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, str) and UUID_RE.match(value), f"{path} expected UUID string"


class DateTime(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, str) and DATETIME_RE.match(value), (
            f"{path} expected UTC datetime, got {value!r}"
        )


class DateStr(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, str) and DATE_RE.match(value), f"{path} expected date"


class Games(Spec):
    def check(self, value: object, path: str) -> None:
        assert isinstance(value, list), f"{path} expected a list of score pairs"
        for index, game in enumerate(value):
            assert isinstance(game, list) and len(game) == 2, f"{path}[{index}]"
            assert all(isinstance(score, int) and not isinstance(score, bool) for score in game)


def paginated(item: Spec) -> Obj:
    return Obj(items=Arr(item), total=Int(), page=Int(), page_size=Int())


PLAYER = Obj(
    id=Uuid(),
    display_name=Text(),
    avatar_url=Opt(Text()),
    current_rating=Int(),
    is_active=Bool(),
)
STREAK = Obj(type=Lit("W", "L"), count=Int())
STATS = Obj(
    matches_played=Int(),
    wins=Int(),
    losses=Int(),
    win_rate=Opt(Num()),
    current_streak=Opt(STREAK),
    recent_form=Arr(Lit("W", "L")),
    last_rating_change=Opt(Int()),
    rating_change_30d=Int(),
)
RANKING = Obj(
    rank=Int(),
    player=PLAYER,
    rating=Int(),
    highest_rating=Int(),
    matches_played=Int(),
    wins=Int(),
    losses=Int(),
    win_rate=Opt(Num()),
    last_rating_change=Opt(Int()),
    rating_change_30d=Int(),
    recent_form=Arr(Lit("W", "L")),
)
RATING_CHANGE = Obj(player_id=Uuid(), old_rating=Int(), new_rating=Int(), rating_change=Int())
TOURNAMENT_REF = Obj(id=Uuid(), name=Text())
MATCH = Obj(
    id=Uuid(),
    player_a=PLAYER,
    player_b=PLAYER,
    winner_id=Uuid(),
    match_date=DateTime(),
    status=Lit("completed", "canceled", "disputed"),
    tournament=Opt(TOURNAMENT_REF),
    game_scores=Opt(Games()),
    notes=Opt(Text()),
    rating_changes=Arr(RATING_CHANGE),
    deleted_at=Exact(None),
    created_at=DateTime(),
    updated_at=DateTime(),
)
PLAYER_MATCH = Obj(
    id=Uuid(),
    player_a=PLAYER,
    player_b=PLAYER,
    winner_id=Uuid(),
    match_date=DateTime(),
    status=Lit("completed", "canceled", "disputed"),
    tournament=Opt(TOURNAMENT_REF),
    game_scores=Opt(Games()),
    notes=Opt(Text()),
    rating_changes=Arr(RATING_CHANGE),
    deleted_at=Exact(None),
    created_at=DateTime(),
    updated_at=DateTime(),
    opponent=PLAYER,
    result=Lit("W", "L"),
    rating_change=Opt(Int()),
)
ACHIEVEMENT = Obj(
    id=Uuid(),
    name=Text(),
    description=Text(),
    icon=Text(),
    criteria_type=Text(),
    criteria_value=Opt(Int()),
    is_active=Bool(),
    awarded_count=Int(),
)
PLAYER_ACHIEVEMENT = Obj(
    id=Uuid(),
    achievement=ACHIEVEMENT,
    awarded_at=DateTime(),
    notes=Opt(Text()),
)
AWARD = Obj(id=Uuid(), player=PLAYER, achievement=ACHIEVEMENT, awarded_at=DateTime())
TOURNAMENT = Obj(
    id=Uuid(),
    name=Text(),
    description=Opt(Text()),
    format=Lit("single_elimination"),
    status=Lit("draft", "in_progress", "completed", "canceled"),
    start_date=Opt(DateStr()),
    end_date=Opt(DateStr()),
    participant_count=Int(),
    champion=Opt(PLAYER),
    created_at=DateTime(),
)
PARTICIPANT = Obj(player=PLAYER, seed=Opt(Int()), final_position=Opt(Int()))
TOURNAMENT_DETAIL = Obj(
    id=Uuid(),
    name=Text(),
    description=Opt(Text()),
    format=Lit("single_elimination"),
    status=Lit("draft", "in_progress", "completed", "canceled"),
    start_date=Opt(DateStr()),
    end_date=Opt(DateStr()),
    participant_count=Int(),
    champion=Opt(PLAYER),
    created_at=DateTime(),
    participants=Arr(PARTICIPANT),
    bracket_generated=Bool(),
    runner_up=Opt(PLAYER),
    updated_at=DateTime(),
)
BRACKET_MATCH = Obj(
    id=Uuid(),
    round=Int(),
    position=Int(),
    player_a=Opt(PLAYER),
    player_b=Opt(PLAYER),
    seed_a=Opt(Int()),
    seed_b=Opt(Int()),
    winner_id=Opt(Uuid()),
    is_bye=Bool(),
    status=Lit("pending", "ready", "completed", "bye"),
    match_id=Opt(Uuid()),
    match_date=Opt(DateTime()),
    game_scores=Opt(Games()),
)
BRACKET = Obj(
    tournament_id=Uuid(),
    rounds=Arr(Obj(round=Int(), name=Text(), matches=Arr(BRACKET_MATCH))),
)
TOTALS = Obj(
    active_players=Int(),
    total_matches=Int(),
    matches_this_month=Int(),
    tournaments_completed=Int(),
)
PROGRESS = Obj(
    player=PLAYER,
    points=Arr(Obj(match_date=Opt(DateTime()), rating=Int())),
)
DASHBOARD = Obj(
    leader=Opt(RANKING),
    top_players=Arr(RANKING),
    totals=TOTALS,
    recent_matches=Arr(MATCH),
    rating_progression=Arr(PROGRESS),
    active_tournament=Opt(TOURNAMENT),
    recent_achievements=Arr(AWARD),
    last_updated=Opt(DateTime()),
)
RANKINGS = Obj(items=Arr(RANKING), last_updated=Opt(DateTime()))
MONTH_REF = Obj(year=Int(), month=Int())
MONTHLY_ITEM = Obj(
    rank=Int(),
    player=PLAYER,
    rating=Int(),
    rank_change=Opt(Int()),
    wins=Int(),
    losses=Int(),
    matches_played=Int(),
    rating_change_during_month=Int(),
)
MONTHLY = Obj(
    available_months=Arr(MONTH_REF),
    year=Opt(Int()),
    month=Opt(Int()),
    items=Arr(MONTHLY_ITEM),
)
PLAYER_LIST_ITEM = Obj(
    id=Uuid(),
    display_name=Text(),
    avatar_url=Opt(Text()),
    current_rating=Int(),
    is_active=Bool(),
    highest_rating=Int(),
    rank=Opt(Int()),
    matches_played=Int(),
    wins=Int(),
    losses=Int(),
    win_rate=Opt(Num()),
)
PLAYERS = Obj(items=Arr(PLAYER_LIST_ITEM))
PROFILE = Obj(
    id=Uuid(),
    display_name=Text(),
    avatar_url=Opt(Text()),
    current_rating=Int(),
    is_active=Bool(),
    highest_rating=Int(),
    rank=Opt(Int()),
    stats=STATS,
    created_at=DateTime(),
    updated_at=DateTime(),
)
HISTORY_POINT = Obj(
    match_id=Uuid(),
    match_date=DateTime(),
    old_rating=Int(),
    new_rating=Int(),
    rating_change=Int(),
    opponent=PLAYER,
    result=Lit("W", "L"),
)
HISTORY = Obj(player_id=Uuid(), starting_rating=Exact(1500), points=Arr(HISTORY_POINT))
PLAYER_MONTH = Obj(
    year=Int(),
    month=Int(),
    rating=Int(),
    rank=Int(),
    wins=Int(),
    losses=Int(),
    matches_played=Int(),
    rating_change_during_month=Int(),
)
HEAD_TO_HEAD = Obj(
    player_a=PLAYER,
    player_b=PLAYER,
    total_matches=Int(),
    player_a_wins=Int(),
    player_b_wins=Int(),
    player_a_win_rate=Opt(Num()),
    player_b_win_rate=Opt(Num()),
    current_streak=Opt(Obj(player_id=Uuid(), count=Int())),
    player_a_net_rating_change=Int(),
    matches=Arr(MATCH),
)
HEALTH = Obj(status=Text(), database=Text())


def ok(client: TestClient, path: str, params: dict | None = None) -> dict:
    response = client.get(path, params=params)
    assert response.status_code == 200, (path, response.status_code, response.text)
    body = response.json()
    assert isinstance(body, dict)
    return body


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]


def parse_dt(value: str) -> datetime:
    DATETIME_RE.fullmatch(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_empty_public_responses_match_the_contract(api_client) -> None:
    client, _factory = api_client
    health = ok(client, f"{API}/health")
    HEALTH.check(health, "health")
    assert health == {"status": "ok", "database": "ok"}

    dashboard = ok(client, f"{API}/dashboard")
    DASHBOARD.check(dashboard, "dashboard")
    assert dashboard["leader"] is None
    assert dashboard["top_players"] == []
    assert dashboard["totals"] == {
        "active_players": 0,
        "total_matches": 0,
        "matches_this_month": 0,
        "tournaments_completed": 0,
    }
    assert dashboard["recent_matches"] == []
    assert dashboard["rating_progression"] == []
    assert dashboard["active_tournament"] is None
    assert dashboard["recent_achievements"] == []
    assert dashboard["last_updated"] is None

    rankings = ok(client, f"{API}/rankings")
    RANKINGS.check(rankings, "rankings")
    assert rankings["items"] == [] and rankings["last_updated"] is None

    monthly = ok(client, f"{API}/rankings/monthly")
    MONTHLY.check(monthly, "monthly")
    assert monthly["available_months"] == []
    assert monthly["year"] is None and monthly["month"] is None and monthly["items"] == []

    players = ok(client, f"{API}/players")
    PLAYERS.check(players, "players")
    assert players["items"] == []

    matches = ok(client, f"{API}/matches")
    paginated(MATCH).check(matches, "matches")
    assert matches == {"items": [], "total": 0, "page": 1, "page_size": 20}

    tournaments = ok(client, f"{API}/tournaments")
    Obj(items=Arr(TOURNAMENT)).check(tournaments, "tournaments")
    assert tournaments["items"] == []

    achievements = ok(client, f"{API}/achievements")
    Obj(items=Arr(ACHIEVEMENT)).check(achievements, "achievements")
    assert achievements["items"] == []

    missing = uuid.uuid4()
    other = uuid.uuid4()
    assert_error(client.get(f"{API}/players/{missing}"), 404, "not_found")
    assert_error(client.get(f"{API}/players/{missing}/matches"), 404, "not_found")
    assert_error(client.get(f"{API}/players/{missing}/rating-history"), 404, "not_found")
    assert_error(client.get(f"{API}/players/{missing}/monthly"), 404, "not_found")
    assert_error(client.get(f"{API}/players/{missing}/achievements"), 404, "not_found")
    assert_error(client.get(f"{API}/matches/{missing}"), 404, "not_found")
    assert_error(client.get(f"{API}/tournaments/{missing}"), 404, "not_found")
    assert_error(client.get(f"{API}/tournaments/{missing}/bracket"), 404, "not_found")
    assert_error(client.get(f"{API}/head-to-head/{missing}/{other}"), 404, "not_found")
    assert_error(
        client.get(f"{API}/rankings/monthly", params={"year": 1999, "month": 1}),
        404,
        "not_found",
    )


def test_populated_responses_have_documented_fields(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        alice = make_player(db, "Alice")
        boris = make_player(db, "Boris")
        clara = make_player(db, "Clara")
        live = make_tournament(db, "Club Open", status="in_progress")
        add_participant(db, live, alice, seed=1)
        add_participant(db, live, boris, seed=2)
        add_bracket_slot(db, live, round_number=1, position=0, player_a=alice, player_b=boris)
        completed = make_tournament(db, "Old Open", status="completed")
        add_participant(db, completed, alice, seed=1, final_position=1)
        add_participant(db, completed, boris, seed=2, final_position=2)
        make_tournament(db, "Spring Cup", status="draft")
        badge = make_achievement(db, "First Win")
        make_achievement(db, "Hidden Cup", is_active=False)
        award(db, alice, badge, notes="opening night")
        played = make_match(
            db,
            alice,
            boris,
            winner=alice,
            match_date=datetime(2026, 4, 1, 12, tzinfo=UTC),
            game_scores=[[21, 15]],
            notes="final",
            tournament_id=live.id,
        )
        alice_id, boris_id, clara_id = str(alice.id), str(boris.id), str(clara.id)
        live_id, completed_id, match_id = str(live.id), str(completed.id), str(played.id)
    finally:
        db.close()

    dashboard = ok(client, f"{API}/dashboard")
    DASHBOARD.check(dashboard, "dashboard")
    rankings = ok(client, f"{API}/rankings")
    RANKINGS.check(rankings, "rankings")
    ok(client, f"{API}/rankings", params={"include_inactive": "true", "sort": "rating"})
    monthly = ok(client, f"{API}/rankings/monthly")
    MONTHLY.check(monthly, "monthly")
    assert monthly["year"] is not None and monthly["items"]
    month = ok(
        client,
        f"{API}/rankings/monthly",
        params={"year": monthly["year"], "month": monthly["month"]},
    )
    MONTHLY.check(month, "monthly-selected")

    players = ok(client, f"{API}/players")
    PLAYERS.check(players, "players")
    found = ok(client, f"{API}/players", params={"search": "ALI"})
    PLAYERS.check(found, "players-search")
    assert [item["display_name"] for item in found["items"]] == ["Alice"]

    profile = ok(client, f"{API}/players/{alice_id}")
    PROFILE.check(profile, "profile")
    assert profile["display_name"] == "Alice"
    player_matches = ok(client, f"{API}/players/{alice_id}/matches")
    paginated(PLAYER_MATCH).check(player_matches, "player-matches")
    history = ok(client, f"{API}/players/{alice_id}/rating-history")
    HISTORY.check(history, "history")
    assert history["points"]
    player_months = ok(client, f"{API}/players/{alice_id}/monthly")
    Obj(items=Arr(PLAYER_MONTH)).check(player_months, "player-monthly")
    awards = ok(client, f"{API}/players/{alice_id}/achievements")
    Obj(items=Arr(PLAYER_ACHIEVEMENT)).check(awards, "player-achievements")
    assert awards["items"]

    matches = ok(client, f"{API}/matches")
    paginated(MATCH).check(matches, "matches")
    detail = ok(client, f"{API}/matches/{match_id}")
    MATCH.check(detail, "match")
    assert detail["tournament"]["id"] == live_id
    assert detail["rating_changes"]
    head = ok(client, f"{API}/head-to-head/{alice_id}/{boris_id}")
    HEAD_TO_HEAD.check(head, "head-to-head")

    tournaments = ok(client, f"{API}/tournaments")
    Obj(items=Arr(TOURNAMENT)).check(tournaments, "tournaments")
    in_progress = ok(client, f"{API}/tournaments", params={"status": "in_progress"})
    assert [item["id"] for item in in_progress["items"]] == [live_id]
    detail_t = ok(client, f"{API}/tournaments/{completed_id}")
    TOURNAMENT_DETAIL.check(detail_t, "tournament")
    assert detail_t["champion"]["display_name"] == "Alice"
    assert detail_t["runner_up"]["display_name"] == "Boris"
    bracket = ok(client, f"{API}/tournaments/{live_id}/bracket")
    BRACKET.check(bracket, "bracket")
    assert bracket["rounds"][0]["name"] == "Final"
    assert bracket["rounds"][0]["matches"][0]["status"] == "ready"

    achievements = ok(client, f"{API}/achievements")
    Obj(items=Arr(ACHIEVEMENT)).check(achievements, "achievements")
    assert [item["name"] for item in achievements["items"]] == ["First Win"]
    including = ok(client, f"{API}/achievements", params={"include_inactive": "true"})
    names = {item["name"] for item in including["items"]}
    assert names == {"First Win", "Hidden Cup"}
    empty_awards = ok(client, f"{API}/players/{clara_id}/achievements")
    assert empty_awards == {"items": []}
    empty_history = ok(client, f"{API}/players/{clara_id}/rating-history")
    HISTORY.check(empty_history, "empty-history")
    assert empty_history["points"] == []
    assert empty_history["starting_rating"] == 1500


def test_dashboard_aggregates_match_rankings_and_matches(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        names = ["Ada", "Bea", "Cid", "Dot", "Eve", "Fay"]
        players = [make_player(db, name) for name in names]
        base = datetime(2026, 1, 5, 12, tzinfo=UTC)
        for index in range(5):
            make_match(
                db,
                players[index],
                players[(index + 1) % 6],
                winner=players[index],
                match_date=base + timedelta(days=index),
            )
        recent = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=1)
        make_match(db, players[0], players[1], winner=players[0], match_date=recent)
        make_match(
            db,
            players[2],
            players[3],
            winner=players[2],
            match_date=recent + timedelta(minutes=1),
            status="canceled",
        )
        make_tournament(db, "Finished", status="completed")
        live = make_tournament(db, "Live", status="in_progress")
        make_tournament(db, "Draft", status="draft")
        live_id = str(live.id)
    finally:
        db.close()

    dashboard = ok(client, f"{API}/dashboard")
    DASHBOARD.check(dashboard, "dashboard")
    rankings = ok(client, f"{API}/rankings")
    completed = ok(client, f"{API}/matches", params={"status": "completed", "page_size": 100})
    assert dashboard["leader"] == rankings["items"][0]
    assert dashboard["top_players"] == rankings["items"][:5]
    assert len(rankings["items"]) == 6
    assert dashboard["totals"]["active_players"] == len(ok(client, f"{API}/players")["items"])
    assert dashboard["totals"]["active_players"] == 6
    assert dashboard["totals"]["total_matches"] == completed["total"]
    assert dashboard["totals"]["total_matches"] == 6
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    in_month = [item for item in completed["items"] if parse_dt(item["match_date"]) >= month_start]
    assert dashboard["totals"]["matches_this_month"] == len(in_month)
    assert dashboard["totals"]["tournaments_completed"] == 1
    recent_ids = [item["id"] for item in dashboard["recent_matches"]]
    assert recent_ids == [item["id"] for item in completed["items"][:5]]
    assert all(item["status"] == "completed" for item in dashboard["recent_matches"])
    assert len(dashboard["recent_matches"]) == 5
    assert parse_dt(dashboard["last_updated"]) == parse_dt(rankings["last_updated"])
    assert dashboard["active_tournament"]["id"] == live_id
    assert dashboard["active_tournament"]["status"] == "in_progress"
    assert len(dashboard["rating_progression"]) == 5
    paired = zip(dashboard["rating_progression"], dashboard["top_players"], strict=True)
    for series, entry in paired:
        assert series["player"]["id"] == entry["player"]["id"]
        assert series["points"][0] == {"match_date": None, "rating": 1500}
        history = ok(client, f"{API}/players/{entry['player']['id']}/rating-history")
        assert [point["rating"] for point in series["points"][1:]] == [
            point["new_rating"] for point in history["points"]
        ]


def test_match_filters_pagination_and_deleted_matches(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        alice = make_player(db, "Alice")
        bob = make_player(db, "Bob")
        carol = make_player(db, "Carol")
        club = make_tournament(db, "Club Night")
        early = make_match(
            db,
            alice,
            bob,
            winner=alice,
            match_date=datetime(2026, 1, 10, 12, tzinfo=UTC),
            tournament_id=club.id,
            notes="club night",
        )
        boundary = make_match(
            db,
            alice,
            carol,
            winner=carol,
            match_date=datetime(2026, 1, 20, 23, 30, tzinfo=UTC),
        )
        canceled = make_match(
            db,
            bob,
            carol,
            winner=bob,
            match_date=datetime(2026, 2, 5, 12, tzinfo=UTC),
            status="canceled",
        )
        disputed = make_match(
            db,
            alice,
            bob,
            winner=bob,
            match_date=datetime(2026, 2, 15, 12, tzinfo=UTC),
            status="disputed",
        )
        removed = make_match(
            db,
            alice,
            bob,
            winner=alice,
            match_date=datetime(2026, 3, 1, 12, tzinfo=UTC),
        )
        from app.services.match_service import delete_match

        delete_match(db, removed.id, "qa", "qa")
        ids = {
            "early": str(early.id),
            "boundary": str(boundary.id),
            "canceled": str(canceled.id),
            "disputed": str(disputed.id),
            "removed": str(removed.id),
            "alice": str(alice.id),
            "carol": str(carol.id),
            "club": str(club.id),
        }
    finally:
        db.close()

    default = ok(client, f"{API}/matches")
    assert default["total"] == 2
    assert [item["id"] for item in default["items"]] == [ids["boundary"], ids["early"]]
    assert all(item["status"] == "completed" for item in default["items"])

    everything = ok(client, f"{API}/matches", params={"status": "all", "page_size": 50})
    visible = {item["id"] for item in everything["items"]}
    assert visible == {ids["early"], ids["boundary"], ids["canceled"], ids["disputed"]}
    assert ids["removed"] not in visible
    assert_error(client.get(f"{API}/matches/{ids['removed']}"), 404, "not_found")

    only_canceled = ok(client, f"{API}/matches", params={"status": "canceled"})
    assert [item["id"] for item in only_canceled["items"]] == [ids["canceled"]]
    only_disputed = ok(client, f"{API}/matches", params={"status": "disputed"})
    assert [item["id"] for item in only_disputed["items"]] == [ids["disputed"]]

    carol_matches = ok(
        client,
        f"{API}/matches",
        params={"player_id": ids["carol"], "status": "all"},
    )
    assert {item["id"] for item in carol_matches["items"]} == {ids["boundary"], ids["canceled"]}

    found = ok(client, f"{API}/matches", params={"search": "cArOl", "status": "all"})
    assert {item["id"] for item in found["items"]} == {ids["boundary"], ids["canceled"]}
    assert ok(client, f"{API}/matches", params={"search": "zzz", "status": "all"})["total"] == 0

    on_day = ok(
        client,
        f"{API}/matches",
        params={"date_from": "2026-01-20", "date_to": "2026-01-20", "status": "all"},
    )
    assert [item["id"] for item in on_day["items"]] == [ids["boundary"]]
    before = ok(
        client,
        f"{API}/matches",
        params={"date_to": "2026-01-19", "status": "all"},
    )
    assert [item["id"] for item in before["items"]] == [ids["early"]]
    after = ok(
        client,
        f"{API}/matches",
        params={"date_from": "2026-01-21", "status": "all"},
    )
    assert ids["boundary"] not in {item["id"] for item in after["items"]}

    club_matches = ok(
        client,
        f"{API}/matches",
        params={"tournament_id": ids["club"], "status": "all"},
    )
    assert [item["id"] for item in club_matches["items"]] == [ids["early"]]

    wide = ok(client, f"{API}/matches", params={"page_size": 100, "status": "all"})
    assert wide["page_size"] == 100
    assert_error(client.get(f"{API}/matches", params={"page_size": 101}), 422, "validation_error")
    assert_error(client.get(f"{API}/matches", params={"page_size": 0}), 422, "validation_error")
    assert_error(client.get(f"{API}/matches", params={"page": 0}), 422, "validation_error")
    assert_error(
        client.get(f"{API}/players/{ids['alice']}/matches", params={"page_size": 101}),
        422,
        "validation_error",
    )


def test_pagination_returns_newest_matches_first(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        left = make_player(db, "Left")
        right = make_player(db, "Right")
        ordered = []
        for day in range(1, 6):
            match = make_match(
                db,
                left,
                right,
                winner=left,
                match_date=datetime(2026, 6, day, 12, tzinfo=UTC),
            )
            ordered.append(str(match.id))
        player_id = str(left.id)
    finally:
        db.close()
    newest_first = list(reversed(ordered))
    page = ok(client, f"{API}/matches", params={"page": 1, "page_size": 2})
    assert page["total"] == 5
    assert page["page"] == 1 and page["page_size"] == 2
    assert [item["id"] for item in page["items"]] == newest_first[:2]
    second = ok(client, f"{API}/matches", params={"page": 2, "page_size": 2})
    assert [item["id"] for item in second["items"]] == newest_first[2:4]
    third = ok(client, f"{API}/matches", params={"page": 3, "page_size": 2})
    assert [item["id"] for item in third["items"]] == newest_first[4:]
    player_page = ok(
        client,
        f"{API}/players/{player_id}/matches",
        params={"page": 1, "page_size": 2},
    )
    paginated(PLAYER_MATCH).check(player_page, "player-page")
    assert player_page["total"] == 5
    assert [item["id"] for item in player_page["items"]] == newest_first[:2]


def test_head_to_head_totals_same_player_and_unknown(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        alice = make_player(db, "Alice")
        bob = make_player(db, "Bob")
        carol = make_player(db, "Carol")
        make_match(db, alice, bob, winner=alice, match_date=datetime(2026, 4, 1, 12, tzinfo=UTC))
        make_match(db, bob, alice, winner=bob, match_date=datetime(2026, 4, 2, 12, tzinfo=UTC))
        make_match(
            db,
            alice,
            bob,
            winner=alice,
            match_date=datetime(2026, 4, 3, 12, tzinfo=UTC),
            status="canceled",
        )
        make_match(
            db,
            alice,
            bob,
            winner=alice,
            match_date=datetime(2026, 4, 4, 12, tzinfo=UTC),
            status="disputed",
        )
        make_match(db, alice, carol, winner=alice, match_date=datetime(2026, 4, 5, 12, tzinfo=UTC))
        quiet_a = make_player(db, "Quiet A")
        quiet_b = make_player(db, "Quiet B")
        ids = {
            "alice": str(alice.id),
            "bob": str(bob.id),
            "carol": str(carol.id),
            "quiet_a": str(quiet_a.id),
            "quiet_b": str(quiet_b.id),
        }
    finally:
        db.close()

    body = ok(client, f"{API}/head-to-head/{ids['alice']}/{ids['bob']}")
    HEAD_TO_HEAD.check(body, "head-to-head")
    assert body["total_matches"] == 2
    assert body["player_a_wins"] == 1 and body["player_b_wins"] == 1
    assert body["player_a_win_rate"] == 0.5 and body["player_b_win_rate"] == 0.5
    assert body["player_a_net_rating_change"] == 16 - elo_delta(1484, 1516)
    assert body["player_a_net_rating_change"] == -1
    assert body["current_streak"]["player_id"] == ids["bob"]
    assert body["current_streak"]["count"] == 1
    assert [item["winner_id"] for item in body["matches"]] == [ids["bob"], ids["alice"]]
    assert body["matches"][0]["match_date"] > body["matches"][1]["match_date"]

    swapped = ok(client, f"{API}/head-to-head/{ids['bob']}/{ids['alice']}")
    assert swapped["player_a_wins"] == body["player_b_wins"]
    assert swapped["player_b_wins"] == body["player_a_wins"]
    assert swapped["player_a_net_rating_change"] == -body["player_a_net_rating_change"]
    assert swapped["player_a"]["id"] == ids["bob"]

    none = ok(client, f"{API}/head-to-head/{ids['quiet_a']}/{ids['quiet_b']}")
    assert none["total_matches"] == 0
    assert none["player_a_wins"] == 0 and none["player_b_wins"] == 0
    assert none["player_a_win_rate"] is None and none["player_b_win_rate"] is None
    assert none["current_streak"] is None
    assert none["player_a_net_rating_change"] == 0
    assert none["matches"] == []

    other = ok(client, f"{API}/head-to-head/{ids['alice']}/{ids['carol']}")
    assert other["total_matches"] == 1
    assert other["player_a_wins"] == 1

    assert_error(
        client.get(f"{API}/head-to-head/{ids['alice']}/{ids['alice']}"),
        422,
        "business_rule_violation",
    )
    assert_error(
        client.get(f"{API}/head-to-head/{ids['alice']}/{uuid.uuid4()}"),
        404,
        "not_found",
    )
    assert_error(
        client.get(f"{API}/head-to-head/{uuid.uuid4()}/{uuid.uuid4()}"),
        404,
        "not_found",
    )


def test_rankings_use_competition_ties_and_keep_ranks_when_sorted(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        wynn = make_player(db, "Wynn")
        lars = make_player(db, "Lars")
        make_player(db, "Tess")
        make_player(db, "Una")
        make_match(db, wynn, lars, winner=wynn, match_date=datetime(2026, 5, 1, 12, tzinfo=UTC))
    finally:
        db.close()

    body = ok(client, f"{API}/rankings")
    RANKINGS.check(body, "rankings")
    rows = [(item["player"]["display_name"], item["rank"]) for item in body["items"]]
    assert rows == [("Wynn", 1), ("Tess", 2), ("Una", 2), ("Lars", 4)]
    by_name = {item["player"]["display_name"]: item for item in body["items"]}
    assert by_name["Tess"]["rating"] == 1500
    assert by_name["Tess"]["matches_played"] == 0
    assert by_name["Tess"]["wins"] == 0 and by_name["Tess"]["losses"] == 0
    assert by_name["Tess"]["win_rate"] is None
    assert by_name["Wynn"]["rating"] == 1516
    assert by_name["Wynn"]["highest_rating"] == 1516
    assert by_name["Wynn"]["last_rating_change"] == 16
    assert by_name["Wynn"]["recent_form"] == ["W"]
    assert by_name["Lars"]["rating"] == 1484
    assert by_name["Lars"]["highest_rating"] == 1500
    assert by_name["Lars"]["last_rating_change"] == -16
    assert by_name["Lars"]["recent_form"] == ["L"]

    by_wins = ok(client, f"{API}/rankings", params={"sort": "wins", "order": "desc"})
    resorted = {item["player"]["display_name"]: item["rank"] for item in by_wins["items"]}
    assert resorted == {"Wynn": 1, "Tess": 2, "Una": 2, "Lars": 4}


def test_equal_ratings_share_a_rank_when_win_counts_differ(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        ace = make_player(db, "Ace")
        bea = make_player(db, "Bea")
        cal = make_player(db, "Cal")
        make_player(db, "Dee")
        day = datetime(2026, 1, 1, 12, tzinfo=UTC)
        make_match(db, ace, bea, winner=ace, match_date=day)
        make_match(db, cal, ace, winner=cal, match_date=day.replace(day=2))
        make_match(db, cal, ace, winner=cal, match_date=day.replace(day=3))
    finally:
        db.close()

    body = ok(client, f"{API}/rankings")
    ranks = {item["player"]["display_name"]: item["rank"] for item in body["items"]}
    order = [item["player"]["display_name"] for item in body["items"]]
    assert order == ["Cal", "Dee", "Ace", "Bea"]
    assert ranks == {"Cal": 1, "Dee": 2, "Ace": 3, "Bea": 3}
    ratings = {item["player"]["display_name"]: item["rating"] for item in body["items"]}
    assert ratings["Ace"] == ratings["Bea"] == 1484
    assert ratings["Cal"] == 1532
    assert ratings["Dee"] == 1500


def test_inactive_players_stay_out_of_default_lists_and_remain_on_profile(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        alice = make_player(db, "Alice")
        boris = make_player(db, "Boris")
        match = make_match(
            db,
            alice,
            boris,
            winner=alice,
            match_date=datetime(2026, 5, 2, 12, tzinfo=UTC),
        )
        from app.services.player_service import deactivate_player

        deactivate_player(db, alice.id, actor="qa")
        alice_id, boris_id, match_id = str(alice.id), str(boris.id), str(match.id)
    finally:
        db.close()

    default_rankings = ok(client, f"{API}/rankings")
    assert [item["player"]["display_name"] for item in default_rankings["items"]] == ["Boris"]
    assert default_rankings["items"][0]["rank"] == 1
    assert default_rankings["items"][0]["rating"] == 1484

    with_inactive = ok(client, f"{API}/rankings", params={"include_inactive": "true"})
    included = {item["player"]["display_name"]: item for item in with_inactive["items"]}
    assert set(included) == {"Alice", "Boris"}
    assert included["Alice"]["player"]["is_active"] is False
    assert included["Alice"]["rating"] == 1516
    assert included["Alice"]["rank"] == 1
    assert included["Boris"]["rank"] == 2

    directory = ok(client, f"{API}/players")
    assert [item["display_name"] for item in directory["items"]] == ["Boris"]
    everyone = ok(client, f"{API}/players", params={"include_inactive": "true"})
    inactive = next(item for item in everyone["items"] if item["display_name"] == "Alice")
    assert inactive["rank"] is None
    assert inactive["is_active"] is False
    assert inactive["current_rating"] == 1516
    active = next(item for item in everyone["items"] if item["display_name"] == "Boris")
    assert active["rank"] == 1

    profile = ok(client, f"{API}/players/{alice_id}")
    PROFILE.check(profile, "inactive-profile")
    assert profile["is_active"] is False
    assert profile["rank"] is None
    assert profile["current_rating"] == 1516
    assert profile["stats"]["wins"] == 1

    matches = ok(client, f"{API}/matches")
    assert matches["items"][0]["id"] == match_id
    assert matches["items"][0]["player_a"]["display_name"] == "Alice"
    assert matches["items"][0]["player_a"]["is_active"] is False
    own = ok(client, f"{API}/players/{alice_id}/matches")
    assert own["total"] == 1
    assert own["items"][0]["result"] == "W"
    assert own["items"][0]["opponent"]["id"] == boris_id


def test_rating_history_is_chronological_with_opponent_and_result(api_client) -> None:
    client, factory = api_client
    db = factory()
    try:
        alice = make_player(db, "Alice")
        boris = make_player(db, "Boris")
        march = make_match(
            db,
            alice,
            boris,
            winner=alice,
            match_date=datetime(2026, 3, 1, 12, tzinfo=UTC),
        )
        january = make_match(
            db,
            alice,
            boris,
            winner=alice,
            match_date=datetime(2026, 1, 5, 12, tzinfo=UTC),
        )
        alice_id = str(alice.id)
        january_id, march_id = str(january.id), str(march.id)
        boris_id = str(boris.id)
    finally:
        db.close()

    history = ok(client, f"{API}/players/{alice_id}/rating-history")
    HISTORY.check(history, "history")
    assert history["starting_rating"] == 1500
    points = history["points"]
    assert [point["match_id"] for point in points] == [january_id, march_id]
    assert points[0]["old_rating"] == 1500
    assert points[0]["new_rating"] == 1516
    assert points[0]["rating_change"] == 16
    assert points[0]["result"] == "W"
    assert points[0]["opponent"]["id"] == boris_id
    assert points[0]["opponent"]["display_name"] == "Boris"
    assert points[1]["old_rating"] == 1516
    assert points[1]["new_rating"] == 1531
    assert points[1]["rating_change"] == 15
    assert points[1]["new_rating"] == points[1]["old_rating"] + points[1]["rating_change"]
    assert parse_dt(points[0]["match_date"]) < parse_dt(points[1]["match_date"])

    boris_history = ok(client, f"{API}/players/{boris_id}/rating-history")
    assert [point["result"] for point in boris_history["points"]] == ["L", "L"]
    assert boris_history["points"][0]["rating_change"] == -16
    assert boris_history["points"][1]["old_rating"] == boris_history["points"][0]["new_rating"]
