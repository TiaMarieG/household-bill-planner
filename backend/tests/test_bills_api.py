import pytest

RENT = {"name": "Rent", "amount": "1200.00", "frequency": "months", "anchor_date": "2026-11-01"}
MEDICINE = {
    "name": "Medicine",
    "amount": "25.00",
    "frequency": "days",
    "interval_count": 28,
    "anchor_date": "2026-11-03",
}


def create(client, payload) -> dict:
    response = client.post("/api/bills", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def occurrences(client, start="2026-11-01", end="2026-11-30") -> list[dict]:
    response = client.get("/api/occurrences", params={"start": start, "end": end})
    assert response.status_code == 200, response.text
    return response.json()


def test_create_and_fetch_bill(client):
    created = create(client, RENT)

    fetched = client.get(f"/api/bills/{created['id']}").json()

    assert fetched == created
    assert fetched["amount"] == "1200.00"
    assert fetched["interval_count"] == 1
    assert fetched["is_active"] is True


def test_response_uses_stored_format(client):
    created = create(client, RENT | {"amount": "1200"})
    updated = client.patch(f"/api/bills/{created['id']}", json={"amount": "1250.5"}).json()

    assert created["amount"] == "1200.00"
    assert updated["amount"] == "1250.50"


def test_name_is_trimmed(client):
    assert create(client, RENT | {"name": "  Rent  "})["name"] == "Rent"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"amount": "0"},
        {"amount": "-10"},
        {"amount": "10.999"},
        {"frequency": "yearly"},
        {"interval_count": 0},
        {"until_date": "2026-10-01"},
    ],
)
def test_create_rejects_invalid_input(client, overrides):
    assert client.post("/api/bills", json=RENT | overrides).status_code == 422


def test_list_hides_archived_bills_by_default(client):
    create(client, RENT)
    archived = create(client, MEDICINE)
    client.patch(f"/api/bills/{archived['id']}", json={"is_active": False})

    active = [b["name"] for b in client.get("/api/bills").json()]
    everything = [b["name"] for b in client.get("/api/bills", params={"include_inactive": True}).json()]

    assert active == ["Rent"]
    assert everything == ["Medicine", "Rent"]


def test_missing_bill_returns_404(client):
    assert client.get("/api/bills/999999").status_code == 404
    assert client.patch("/api/bills/999999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/bills/999999").status_code == 404


def test_patch_changes_only_sent_fields(client):
    bill = create(client, RENT | {"until_date": "2027-06-01"})

    updated = client.patch(f"/api/bills/{bill['id']}", json={"amount": "1250.00"}).json()

    assert updated["amount"] == "1250.00"
    assert updated["until_date"] == "2027-06-01"


def test_patch_null_until_date_clears_it(client):
    bill = create(client, RENT | {"until_date": "2027-06-01"})

    updated = client.patch(f"/api/bills/{bill['id']}", json={"until_date": None}).json()

    assert updated["until_date"] is None


def test_patch_rejects_null_for_required_field(client):
    bill = create(client, RENT)

    assert client.patch(f"/api/bills/{bill['id']}", json={"amount": None}).status_code == 422


def test_patch_rejects_until_before_existing_anchor(client):
    bill = create(client, RENT)

    response = client.patch(f"/api/bills/{bill['id']}", json={"until_date": "2026-10-01"})

    assert response.status_code == 422
    assert client.get(f"/api/bills/{bill['id']}").json()["until_date"] is None


def test_delete_bill(client):
    bill = create(client, RENT)

    assert client.delete(f"/api/bills/{bill['id']}").status_code == 204
    assert client.get(f"/api/bills/{bill['id']}").status_code == 404


def test_occurrences_merge_bills_in_date_order(client):
    create(client, RENT)
    create(client, MEDICINE)

    result = [(o["due_date"], o["name"], o["status"]) for o in occurrences(client)]

    assert result == [
        ("2026-11-01", "Rent", "unpaid"),
        ("2026-11-03", "Medicine", "unpaid"),
    ]


def test_occurrences_exclude_archived_bills(client):
    bill = create(client, RENT)
    client.patch(f"/api/bills/{bill['id']}", json={"is_active": False})

    assert occurrences(client) == []


@pytest.mark.parametrize(
    "params",
    [{"start": "2026-11-30", "end": "2026-11-01"}, {"start": "2026-01-01", "end": "2027-06-01"}],
)
def test_occurrences_reject_bad_ranges(client, params):
    assert client.get("/api/occurrences", params=params).status_code == 422


def test_mark_paid_pending_then_cleared(client):
    bill = create(client, RENT)
    url = f"/api/bills/{bill['id']}/occurrences/2026-11-01"

    pending = client.put(url, json={"status": "paid_pending"}).json()
    cleared = client.put(url, json={"status": "paid_cleared"}).json()

    assert pending["status"] == "paid_pending"
    assert cleared["status"] == "paid_cleared"
    assert occurrences(client)[0]["status"] == "paid_cleared"


def test_status_applies_to_one_due_date_only(client):
    bill = create(client, RENT)
    client.put(f"/api/bills/{bill['id']}/occurrences/2026-11-01", json={"status": "paid_cleared"})

    result = occurrences(client, end="2026-12-31")

    assert [(o["due_date"], o["status"]) for o in result] == [
        ("2026-11-01", "paid_cleared"),
        ("2026-12-01", "unpaid"),
    ]


def test_one_off_amount_override(client):
    bill = create(client, RENT)
    url = f"/api/bills/{bill['id']}/occurrences/2026-11-01"

    overridden = client.put(url, json={"status": "unpaid", "amount_override": "1300.00"}).json()

    assert overridden["amount"] == "1300.00"
    assert overridden["amount_overridden"] is True


def test_resetting_to_unpaid_restores_defaults(client):
    bill = create(client, RENT)
    url = f"/api/bills/{bill['id']}/occurrences/2026-11-01"
    client.put(url, json={"status": "paid_pending", "amount_override": "1300.00"})

    reset = client.put(url, json={"status": "unpaid"}).json()

    assert (reset["status"], reset["amount"], reset["amount_overridden"]) == (
        "unpaid",
        "1200.00",
        False,
    )


def test_status_rejected_for_date_bill_is_not_due(client):
    bill = create(client, RENT)

    response = client.put(
        f"/api/bills/{bill['id']}/occurrences/2026-11-02", json={"status": "paid_cleared"}
    )

    assert response.status_code == 422


def test_unknown_status_rejected(client):
    bill = create(client, RENT)

    response = client.put(f"/api/bills/{bill['id']}/occurrences/2026-11-01", json={"status": "paid"})

    assert response.status_code == 422


def test_schedule_change_drops_statuses_for_dates_that_no_longer_exist(client):
    bill = create(client, MEDICINE)
    client.put(f"/api/bills/{bill['id']}/occurrences/2026-11-03", json={"status": "paid_cleared"})

    client.patch(f"/api/bills/{bill['id']}", json={"anchor_date": "2026-11-05"})
    client.patch(f"/api/bills/{bill['id']}", json={"anchor_date": "2026-11-03"})

    assert occurrences(client)[0]["status"] == "unpaid"


def test_non_schedule_change_keeps_statuses(client):
    bill = create(client, MEDICINE)
    client.put(f"/api/bills/{bill['id']}/occurrences/2026-11-03", json={"status": "paid_cleared"})

    client.patch(f"/api/bills/{bill['id']}", json={"amount": "30.00"})

    assert occurrences(client)[0]["status"] == "paid_cleared"
