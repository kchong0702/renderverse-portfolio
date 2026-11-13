from datetime import UTC, datetime, timedelta

from src.clients.google.client import MISSING_SCOPE
from src.core.config import get_settings
from src.features.calendar import service as calendar_service
from tests.conftest import PREFIX, connect_google

WEEK = {"from": "2026-11-03T00:00:00+08:00", "to": "2026-11-10T00:00:00+08:00"}


async def test_calendar_lists_the_events_in_the_range(client, google):
    await connect_google(client)
    google.events = [
        {
            "id": "e1",
            "summary": "Lumen Pay technical interview",
            "location": "Google Meet",
            "htmlLink": "https://calendar.google.com/event?eid=e1",
            "extendedProperties": {"private": {"ops": "interview"}},
            "start": {"dateTime": "2026-11-04T10:00:00+08:00"},
            "end": {"dateTime": "2026-11-04T11:00:00+08:00"},
        },
        {"id": "e2", "start": {"date": "2026-11-07"}, "end": {"date": "2026-11-08"}},
        {
            "id": "e3",
            "status": "cancelled",
            "start": {"date": "2026-11-05"},
            "end": {"date": "2026-11-06"},
        },
    ]

    response = await client.get(f"{PREFIX}/calendar", params=WEEK)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "e1",
            "title": "Lumen Pay technical interview",
            "start": "2026-11-04T10:00:00+08:00",
            "end": "2026-11-04T11:00:00+08:00",
            "all_day": False,
            "location": "Google Meet",
            "url": "https://calendar.google.com/event?eid=e1",
            "interview": True,
        },
        {
            "id": "e2",
            "title": "",
            "start": "2026-11-07",
            "end": "2026-11-08",
            "all_day": True,
            "location": "",
            "url": "",
            "interview": False,
        },
    ]
    [params] = google.calendar_params
    assert params["timeMin"] == ["2026-11-03T00:00:00+08:00"]
    assert params["timeMax"] == ["2026-11-10T00:00:00+08:00"]
    assert params["singleEvents"] == ["true"]
    assert params["maxResults"] == [str(get_settings().google.calendar_max_events)]


async def test_the_range_needs_time_zones_and_an_order(client):
    await connect_google(client)

    naive = await client.get(
        f"{PREFIX}/calendar",
        params={"from": "2026-11-03T00:00:00", "to": "2026-11-10T00:00:00"},
    )
    backwards = await client.get(
        f"{PREFIX}/calendar", params={"from": WEEK["to"], "to": WEEK["from"]}
    )
    too_long = await client.get(
        f"{PREFIX}/calendar",
        params={
            "from": WEEK["from"],
            "to": (
                datetime.fromisoformat(WEEK["from"])
                + timedelta(days=get_settings().google.calendar_max_days + 1)
            ).isoformat(),
        },
    )

    assert naive.status_code == 422
    assert backwards.status_code == 422
    assert too_long.status_code == 422


async def test_an_expired_grant_asks_to_reconnect(client, google):
    await connect_google(client)
    google.revoked = True

    response = await client.get(f"{PREFIX}/calendar", params=WEEK)

    assert response.status_code == 409
    assert "reconnect" in response.json()["detail"]


INTERVIEW = {
    "title": "Lumen Pay technical interview",
    "start": "2026-11-12T10:00:00+08:00",
    "end": "2026-11-12T11:00:00+08:00",
    "location": "Google Meet",
}


async def test_creating_an_event_adds_it_to_google_calendar(client, google):
    await connect_google(client)

    response = await client.post(
        f"{PREFIX}/calendar/events",
        json=INTERVIEW | {"description": "With Aisha Rahman"},
    )

    assert response.status_code == 201
    assert google.created == [
        {
            "summary": "Lumen Pay technical interview",
            "start": {"dateTime": "2026-11-12T10:00:00+08:00"},
            "end": {"dateTime": "2026-11-12T11:00:00+08:00"},
            "description": "With Aisha Rahman",
            "location": "Google Meet",
            "extendedProperties": {"private": {"ops": "interview"}},
        }
    ]
    assert response.json() == {
        "id": "event-1",
        "title": "Lumen Pay technical interview",
        "start": "2026-11-12T10:00:00+08:00",
        "end": "2026-11-12T11:00:00+08:00",
        "all_day": False,
        "location": "Google Meet",
        "url": "",
        "interview": True,
    }


async def test_an_event_must_end_after_it_starts(client, google):
    await connect_google(client)

    response = await client.post(
        f"{PREFIX}/calendar/events", json=INTERVIEW | {"end": INTERVIEW["start"]}
    )

    assert response.status_code == 422
    assert google.created == []


async def test_a_read_only_grant_asks_to_reconnect_for_events(client, google):
    await connect_google(client)
    google.read_only = True

    response = await client.post(f"{PREFIX}/calendar/events", json=INTERVIEW)

    assert response.status_code == 409
    assert response.json() == {"detail": MISSING_SCOPE}


async def test_free_slots_are_the_work_hours_the_calendar_leaves_open(
    client, google, monkeypatch
):
    monkeypatch.setattr(
        calendar_service, "utcnow", lambda: datetime(2026, 11, 13, 4, tzinfo=UTC)
    )
    await connect_google(client)
    google.events = [
        {
            "id": "busy",
            "start": {"dateTime": "2026-11-16T10:00:00+08:00"},
            "end": {"dateTime": "2026-11-16T11:00:00+08:00"},
        }
    ]

    response = await client.get(f"{PREFIX}/calendar/free-slots")

    assert response.status_code == 200
    assert response.json() == {
        "free_slots": [
            {
                "start": f"2026-11-{day}T{start}:00+08:00",
                "end": f"2026-11-{day}T18:00:00+08:00",
            }
            for day, start in [
                ("16", "11:30"),
                ("17", "09:00"),
                ("18", "09:00"),
                ("19", "09:00"),
                ("20", "09:00"),
            ]
        ],
        "timezone": "Asia/Kuala_Lumpur",
    }


async def test_free_slots_are_in_the_users_time_zone_not_the_calendars(
    client, google, monkeypatch
):
    monkeypatch.setattr(
        calendar_service, "utcnow", lambda: datetime(2026, 11, 13, 4, tzinfo=UTC)
    )
    await connect_google(client)
    await client.patch(
        f"{PREFIX}/settings", json={"scheduling": {"timezone": "America/New_York"}}
    )
    google.events = [
        {
            "id": "busy",
            "start": {"dateTime": "2026-11-13T22:00:00+08:00"},
            "end": {"dateTime": "2026-11-13T23:00:00+08:00"},
        }
    ]

    response = await client.get(f"{PREFIX}/calendar/free-slots")

    assert response.status_code == 200
    assert response.json()["timezone"] == "America/New_York"
    assert response.json()["free_slots"][:2] == [
        {"start": "2026-11-13T10:30:00-05:00", "end": "2026-11-13T18:00:00-05:00"},
        {"start": "2026-11-16T09:00:00-05:00", "end": "2026-11-16T18:00:00-05:00"},
    ]
