import pytest


def test_settings_404_until_saved(client):
    assert client.get("/api/settings").status_code == 404


def test_save_and_replace_settings(client):
    first = client.put(
        "/api/settings", json={"budget_anchor_payday": "2026-11-06", "budget_weeks_per_period": 1}
    )
    second = client.put(
        "/api/settings", json={"budget_anchor_payday": "2026-11-13", "budget_weeks_per_period": 2}
    )

    assert first.status_code == 200
    assert second.json() == {"budget_anchor_payday": "2026-11-13", "budget_weeks_per_period": 2}
    assert client.get("/api/settings").json() == second.json()


@pytest.mark.parametrize("weeks", [0, 5])
def test_settings_reject_invalid_period(client, weeks):
    response = client.put(
        "/api/settings", json={"budget_anchor_payday": "2026-11-06", "budget_weeks_per_period": weeks}
    )

    assert response.status_code == 422
