def test_welcome_notification_and_mark_read(client):
    items = client.get("/api/notifications").json()
    assert len(items) == 1 and items[0]["read_at"] is None
    r = client.post(f"/api/notifications/{items[0]['id']}/read")
    assert r.status_code == 200 and r.json()["read_at"] is not None
    assert client.get("/api/notifications?unread_only=true").json() == []


def test_mark_all_read(client):
    assert client.post("/api/notifications/read-all").json() == {"updated": 1}
    assert client.post("/api/notifications/read-all").json() == {"updated": 0}


def test_missing_notification(client):
    assert client.post("/api/notifications/999/read").status_code == 404
