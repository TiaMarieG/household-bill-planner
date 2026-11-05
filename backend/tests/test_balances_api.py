import pytest


def record(client, amount, as_of) -> dict:
    response = client.post("/api/balances", json={"amount": amount, "as_of_date": as_of})
    assert response.status_code == 201, response.text
    return response.json()


def test_latest_is_404_before_any_balance(client):
    assert client.get("/api/balances/latest").status_code == 404


def test_record_balance_returns_stored_values(client):
    stored = record(client, "1234.5", "2026-11-10")

    assert stored["amount"] == "1234.50"
    assert stored["as_of_date"] == "2026-11-10"
    assert stored["recorded_at"]


def test_negative_balance_is_allowed(client):
    assert record(client, "-42.17", "2026-11-10")["amount"] == "-42.17"


@pytest.mark.parametrize(("as_of", "expected"), [("2026-12-01", 201), ("2026-12-02", 422)])
def test_future_dates_allow_one_day_of_timezone_slack(client, as_of, expected):
    response = client.post("/api/balances", json={"amount": "10", "as_of_date": as_of})

    assert response.status_code == expected


def test_rejects_more_than_two_decimal_places(client):
    response = client.post("/api/balances", json={"amount": "10.001", "as_of_date": "2026-11-10"})

    assert response.status_code == 422


def test_history_is_newest_first_and_limited(client):
    for day in ["2026-11-08", "2026-11-10", "2026-11-09"]:
        record(client, "1", day)

    history = client.get("/api/balances", params={"limit": 2}).json()

    assert [b["as_of_date"] for b in history] == ["2026-11-10", "2026-11-09"]


def test_newest_entry_wins_for_same_date(client):
    record(client, "100.00", "2026-11-10")
    record(client, "150.00", "2026-11-10")

    assert client.get("/api/balances/latest").json()["amount"] == "150.00"


def test_deleting_a_mistake_restores_previous_balance(client):
    record(client, "100.00", "2026-11-09")
    mistake = record(client, "10000.00", "2026-11-10")

    assert client.delete(f"/api/balances/{mistake['id']}").status_code == 204
    assert client.get("/api/balances/latest").json()["amount"] == "100.00"


def test_delete_missing_balance_returns_404(client):
    assert client.delete("/api/balances/999999").status_code == 404
