import pytest

WEEKLY_FRIDAYS = {"budget_anchor_payday": "2026-11-06", "budget_weeks_per_period": 1}
ALEX = {
    "name": "Alex",
    "pay_type": "hourly",
    "hourly_rate": "20.00",
    "withholding_percent": "20.00",
    "anchor_payday": "2026-11-06",
}


def setup_household(client, *earners) -> list[dict]:
    assert client.put("/api/settings", json=WEEKLY_FRIDAYS).status_code == 200
    created = []
    for earner in earners:
        response = client.post("/api/earners", json=earner)
        assert response.status_code == 201, response.text
        created.append(response.json())
    return created


def add_bill(client, name, amount, anchor, frequency="once", **extra) -> dict:
    payload = {"name": name, "amount": amount, "frequency": frequency, "anchor_date": anchor} | extra
    response = client.post("/api/bills", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def set_status(client, bill, due_date, status):
    response = client.put(f"/api/bills/{bill['id']}/occurrences/{due_date}", json={"status": status})
    assert response.status_code == 200, response.text


def record_balance(client, amount, as_of, includes_same_day_pay=None):
    payload = {"amount": amount, "as_of_date": as_of, "includes_same_day_pay": includes_same_day_pay}
    return client.post("/api/balances", json=payload)


def summary(client, windows=3) -> dict:
    response = client.get("/api/summary", params={"windows": windows})
    assert response.status_code == 200, response.text
    return response.json()


def test_full_weekly_projection(client):
    alex, = setup_household(client, ALEX)
    client.put(f"/api/earners/{alex['id']}/hours/2026-11-01", json={"hours": "45"})
    set_status(client, add_bill(client, "Internet", "80.00", "2026-11-07"), "2026-11-07", "paid_cleared")
    add_bill(client, "Water", "45.00", "2026-11-03")
    add_bill(client, "Phone", "65.00", "2026-11-08")
    add_bill(client, "Rent", "1000.00", "2026-11-15")
    assert record_balance(client, "500.00", "2026-11-07").status_code == 201

    windows = summary(client)["windows"]

    assert [(w["start"], w["end"]) for w in windows] == [
        ("2026-11-06", "2026-11-12"),
        ("2026-11-13", "2026-11-19"),
        ("2026-11-20", "2026-11-26"),
    ]
    assert [w["remaining"] for w in windows] == ["390.00", "150.00", "790.00"]
    assert [w["incoming"] for w in windows] == ["0.00", "760.00", "640.00"]
    assert windows[0]["overdue"] == "45.00"
    assert [b["name"] for b in windows[0]["bills"]] == ["Internet", "Phone"]


def test_paycheck_detail_shows_entered_and_default_hours(client):
    alex, = setup_household(client, ALEX)
    client.put(f"/api/earners/{alex['id']}/hours/2026-11-01", json={"hours": "45"})
    record_balance(client, "0", "2026-11-07")

    windows = summary(client)["windows"]
    entered = windows[1]["paychecks"][0]
    defaulted = windows[2]["paychecks"][0]

    assert entered == {
        "earner_id": alex["id"],
        "earner_name": "Alex",
        "payday": "2026-11-13",
        "weeks": [{"week_start": "2026-11-01", "hours": "45.00", "is_default": False}],
        "gross": "950.00",
        "net": "760.00",
        "uses_default_hours": False,
        "deposited": False,
    }
    assert (defaulted["weeks"][0]["hours"], defaulted["uses_default_hours"]) == ("40.00", True)


def test_paycheck_before_balance_date_is_treated_as_deposited(client):
    setup_household(client, ALEX)
    record_balance(client, "1000.00", "2026-11-07")

    first = summary(client, windows=1)["windows"][0]

    assert first["paychecks"][0]["deposited"] is True
    assert first["incoming"] == "0.00"


@pytest.mark.parametrize(("included", "incoming"), [(True, "0.00"), (False, "640.00")])
def test_payday_balance_uses_the_same_day_pay_answer(client, included, incoming):
    setup_household(client, ALEX)
    assert record_balance(client, "1000.00", "2026-11-13", included).status_code == 201

    first = summary(client, windows=1)["windows"][0]

    assert first["paychecks"][0]["deposited"] is included
    assert first["incoming"] == incoming


def test_payday_balance_requires_the_same_day_pay_answer(client):
    setup_household(client, ALEX)

    response = record_balance(client, "1000.00", "2026-11-13")

    assert response.status_code == 422
    assert "Alex" in response.json()["detail"]


def test_same_day_pay_answer_is_dropped_on_non_paydays(client):
    setup_household(client, ALEX)

    stored = record_balance(client, "1000.00", "2026-11-10", True).json()

    assert stored["includes_same_day_pay"] is None


def test_paid_pending_bill_still_reduces_remaining(client):
    setup_household(client)
    set_status(client, add_bill(client, "Car", "300.00", "2026-11-09"), "2026-11-09", "paid_pending")
    record_balance(client, "1000.00", "2026-11-10")

    first = summary(client, windows=1)["windows"][0]

    assert (first["pending_withdrawal"], first["remaining"]) == ("300.00", "700.00")


def test_salaried_paycheck_has_no_hours(client):
    sam, = setup_household(
        client, ALEX | {"name": "Sam", "pay_type": "salary", "annual_salary": "52000"}
    )
    record_balance(client, "0", "2026-11-07")

    paycheck = summary(client, windows=2)["windows"][1]["paychecks"][0]

    assert (paycheck["earner_id"], paycheck["weeks"], paycheck["gross"], paycheck["net"]) == (
        sam["id"],
        [],
        "1000.00",
        "800.00",
    )
    assert paycheck["uses_default_hours"] is False


def test_biweekly_earner_only_appears_on_their_paydays(client):
    setup_household(client, ALEX | {"weeks_per_period": 2})
    record_balance(client, "0", "2026-11-07")

    windows = summary(client, windows=4)["windows"]

    assert [len(w["paychecks"]) for w in windows] == [1, 0, 1, 0]
    assert windows[2]["paychecks"][0]["gross"] == "1600.00"


def test_two_earners_paid_same_day(client):
    setup_household(client, ALEX, ALEX | {"name": "Sam", "hourly_rate": "25.00"})
    record_balance(client, "0", "2026-11-07")

    window = summary(client, windows=2)["windows"][1]

    assert [p["earner_name"] for p in window["paychecks"]] == ["Alex", "Sam"]
    assert window["incoming"] == "1440.00"


def test_archived_earner_is_excluded(client):
    alex, = setup_household(client, ALEX)
    client.patch(f"/api/earners/{alex['id']}", json={"is_active": False})
    record_balance(client, "0", "2026-11-07")

    assert all(w["paychecks"] == [] for w in summary(client)["windows"])


def test_summary_starts_from_latest_balance(client):
    setup_household(client)
    record_balance(client, "100.00", "2026-11-20")
    record_balance(client, "999.00", "2026-11-08")

    result = summary(client, windows=1)

    assert result["balance"]["amount"] == "100.00"
    assert result["windows"][0]["start"] == "2026-11-20"


def test_summary_requires_settings(client):
    record_balance(client, "100.00", "2026-11-08")

    response = client.get("/api/summary")

    assert response.status_code == 409
    assert "settings" in response.json()["detail"]


def test_summary_requires_balance(client):
    setup_household(client)

    response = client.get("/api/summary")

    assert response.status_code == 409
    assert "balance" in response.json()["detail"]


@pytest.mark.parametrize("windows", [0, 27])
def test_summary_window_count_limits(client, windows):
    assert client.get("/api/summary", params={"windows": windows}).status_code == 422


def test_empty_totals_use_two_decimal_places(client):
    setup_household(client)
    record_balance(client, "0", "2026-11-07")

    window = summary(client, windows=1)["windows"][0]

    assert {key: window[key] for key in ("incoming", "unpaid", "pending_withdrawal", "overdue")} == {
        "incoming": "0.00",
        "unpaid": "0.00",
        "pending_withdrawal": "0.00",
        "overdue": "0.00",
    }
