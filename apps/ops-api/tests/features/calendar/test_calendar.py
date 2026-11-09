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
        },
        {
            "id": "e2",
            "title": "",
            "start": "2026-11-07",
            "end": "2026-11-08",
            "all_day": True,
            "location": "",
            "url": "",
        },
    ]
    [params] = google.calendar_params
    assert params["timeMin"] == ["2026-11-03T00:00:00+08:00"]
    assert params["timeMax"] == ["2026-11-10T00:00:00+08:00"]
    assert params["singleEvents"] == ["true"]


async def test_the_range_needs_time_zones_and_an_order(client):
    await connect_google(client)

    naive = await client.get(
        f"{PREFIX}/calendar",
        params={"from": "2026-11-03T00:00:00", "to": "2026-11-10T00:00:00"},
    )
    backwards = await client.get(
        f"{PREFIX}/calendar", params={"from": WEEK["to"], "to": WEEK["from"]}
    )

    assert naive.status_code == 422
    assert backwards.status_code == 422


async def test_an_expired_grant_asks_to_reconnect(client, google):
    await connect_google(client)
    google.revoked = True

    response = await client.get(f"{PREFIX}/calendar", params=WEEK)

    assert response.status_code == 409
    assert "reconnect" in response.json()["detail"]
