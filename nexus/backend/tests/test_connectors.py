import httpx

from nexus.integrations import health
from nexus.integrations.registry import CONNECTORS


def test_list_connectors_initial_state(client):
    items = client.get("/api/connectors").json()
    assert {c["id"] for c in items} == {c.id for c in CONNECTORS}
    assert all(c["last_status"] == "unknown" and c["last_checked_at"] is None for c in items)
    implemented = {c["id"] for c in items if c["implemented"]}
    assert implemented == {"fred", "world-bank", "owid", "eurostat", "gutenberg"}
    # IMF, OECD e BIS sono dichiarati ma non ancora implementati: non risultano attivi.
    assert {c["id"] for c in items if not c["implemented"]} == {"imf", "oecd", "bis"}
    assert all(c["terms_url"].startswith("https://") for c in items)


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_probe_reachable():
    r = health.probe("https://example.org", 1, _mock_client(lambda req: httpx.Response(200)))
    assert r.status == "reachable" and r.http_status == 200 and r.latency_ms is not None


def test_probe_degraded_and_server_error():
    assert health.probe("https://x", 1, _mock_client(lambda r: httpx.Response(429))).status == "degraded"
    assert health.probe("https://x", 1, _mock_client(lambda r: httpx.Response(503))).status == "unreachable"


def test_probe_network_failure_is_an_outcome_not_an_exception():
    def boom(_):
        raise httpx.ConnectError("offline")

    r = health.probe("https://x", 1, _mock_client(boom))
    assert r.status == "unreachable" and "offline" in r.error


def test_check_endpoint_persists_unreachable_source(client, monkeypatch):
    monkeypatch.setattr(
        health, "probe", lambda url, timeout: health.ProbeResult("unreachable", None, None, "ConnectError: offline")
    )
    r = client.post("/api/connectors/world-bank/check")
    assert r.status_code == 200
    body = r.json()
    assert body["last_status"] == "unreachable" and body["last_checked_at"]
    listed = {c["id"]: c for c in client.get("/api/connectors").json()}
    assert listed["world-bank"]["last_error"] == "ConnectError: offline"
    assert client.get("/api/activity").json()[0]["action"] == "connector.check"


def test_check_unknown_connector(client):
    assert client.post("/api/connectors/nope/check").status_code == 404
