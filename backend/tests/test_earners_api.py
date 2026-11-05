import pytest

HOURLY = {
    "name": "Alex",
    "pay_type": "hourly",
    "hourly_rate": "20.00",
    "withholding_percent": "18.45",
    "anchor_payday": "2026-11-06",
}
SALARIED = {
    "name": "Sam",
    "pay_type": "salary",
    "annual_salary": "52000.00",
    "withholding_percent": "20.00",
    "anchor_payday": "2026-11-06",
}


def create(client, payload) -> dict:
    response = client.post("/api/earners", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def hours_url(earner, week_start) -> str:
    return f"/api/earners/{earner['id']}/hours/{week_start}"


def stored_weeks(client, earner) -> list[str]:
    response = client.get(
        f"/api/earners/{earner['id']}/hours", params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    return [week["week_start"] for week in response.json()]


def test_create_hourly_earner_with_defaults(client):
    earner = create(client, HOURLY)

    assert earner["default_weekly_hours"] == "40.00"
    assert earner["overtime_threshold_hours"] == "40.00"
    assert earner["overtime_multiplier"] == "1.50"
    assert earner["weeks_per_period"] == 1
    assert earner["days_from_period_end_to_payday"] == 6
    assert client.get(f"/api/earners/{earner['id']}").json() == earner


def test_create_salaried_earner(client):
    earner = create(client, SALARIED)

    assert (earner["pay_type"], earner["annual_salary"], earner["hourly_rate"]) == (
        "salary",
        "52000.00",
        None,
    )


@pytest.mark.parametrize(
    "payload",
    [
        HOURLY | {"hourly_rate": None},
        SALARIED | {"annual_salary": None},
        HOURLY | {"withholding_percent": "100"},
        HOURLY | {"withholding_percent": "-1"},
        HOURLY | {"withholding_percent": "18.455"},
        HOURLY | {"default_weekly_hours": "169"},
        HOURLY | {"overtime_multiplier": "0.5"},
        HOURLY | {"weeks_per_period": 0},
        HOURLY | {"name": "  "},
    ],
)
def test_create_rejects_invalid_input(client, payload):
    assert client.post("/api/earners", json=payload).status_code == 422


def test_list_hides_archived_people(client):
    create(client, HOURLY)
    sam = create(client, SALARIED)
    client.patch(f"/api/earners/{sam['id']}", json={"is_active": False})

    assert [e["name"] for e in client.get("/api/earners").json()] == ["Alex"]
    assert len(client.get("/api/earners", params={"include_inactive": True}).json()) == 2


def test_missing_earner_returns_404(client):
    assert client.get("/api/earners/999999").status_code == 404
    assert client.patch("/api/earners/999999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/earners/999999").status_code == 404
    assert client.put("/api/earners/999999/hours/2026-11-01", json={"hours": "40"}).status_code == 404


def test_switch_to_salary_keeps_hourly_rate_on_file(client):
    earner = create(client, HOURLY)

    updated = client.patch(
        f"/api/earners/{earner['id']}", json={"pay_type": "salary", "annual_salary": "60000"}
    ).json()

    assert (updated["pay_type"], updated["annual_salary"], updated["hourly_rate"]) == (
        "salary",
        "60000.00",
        "20.00",
    )


def test_switch_to_salary_without_salary_is_rejected_and_nothing_changes(client):
    earner = create(client, HOURLY)

    response = client.patch(f"/api/earners/{earner['id']}", json={"pay_type": "salary"})

    assert response.status_code == 422
    assert client.get(f"/api/earners/{earner['id']}").json()["pay_type"] == "hourly"


def test_patch_rejects_null_for_required_field(client):
    earner = create(client, HOURLY)

    assert client.patch(f"/api/earners/{earner['id']}", json={"name": None}).status_code == 422


def test_record_and_overwrite_hours(client):
    earner = create(client, HOURLY)

    client.put(hours_url(earner, "2026-11-01"), json={"hours": "38.5"})
    updated = client.put(hours_url(earner, "2026-11-01"), json={"hours": "42.25"}).json()

    assert updated == {"earner_id": earner["id"], "week_start": "2026-11-01", "hours": "42.25"}
    assert stored_weeks(client, earner) == ["2026-11-01"]


def test_hours_must_start_on_a_workweek_boundary(client):
    earner = create(client, HOURLY)

    response = client.put(hours_url(earner, "2026-11-02"), json={"hours": "40"})

    assert response.status_code == 422
    assert "workweek" in response.json()["detail"]


@pytest.mark.parametrize("hours", ["-1", "168.01", "40.125"])
def test_hours_reject_invalid_values(client, hours):
    earner = create(client, HOURLY)

    assert client.put(hours_url(earner, "2026-11-01"), json={"hours": hours}).status_code == 422


def test_clearing_hours_falls_back_to_default(client):
    earner = create(client, HOURLY)
    client.put(hours_url(earner, "2026-11-01"), json={"hours": "30"})

    assert client.delete(hours_url(earner, "2026-11-01")).status_code == 204
    assert stored_weeks(client, earner) == []


def test_hours_list_filters_by_range(client):
    earner = create(client, HOURLY)
    for week in ["2026-10-25", "2026-11-01", "2026-11-08"]:
        client.put(hours_url(earner, week), json={"hours": "40"})

    response = client.get(
        f"/api/earners/{earner['id']}/hours", params={"start": "2026-11-01", "end": "2026-11-07"}
    )

    assert [w["week_start"] for w in response.json()] == ["2026-11-01"]


def test_payday_change_drops_hours_that_no_longer_line_up(client):
    earner = create(client, HOURLY)
    client.put(hours_url(earner, "2026-11-01"), json={"hours": "40"})

    client.patch(f"/api/earners/{earner['id']}", json={"anchor_payday": "2026-11-05"})

    assert stored_weeks(client, earner) == []


def test_pay_change_keeps_hours(client):
    earner = create(client, HOURLY)
    client.put(hours_url(earner, "2026-11-01"), json={"hours": "40"})

    client.patch(f"/api/earners/{earner['id']}", json={"hourly_rate": "22.00"})

    assert stored_weeks(client, earner) == ["2026-11-01"]


def test_deleting_earner_removes_their_hours(client):
    earner = create(client, HOURLY)
    client.put(hours_url(earner, "2026-11-01"), json={"hours": "40"})

    assert client.delete(f"/api/earners/{earner['id']}").status_code == 204
    assert client.get(f"/api/earners/{earner['id']}").status_code == 404
