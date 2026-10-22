import os
import tempfile
temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = "sqlite:///" + temp.name
from fastapi.testclient import TestClient
from main import app

def test_issue_lifecycle():
    with TestClient(app) as client:
        r = client.post("/issues", json={"title":"Broken water cooler","description":"Cooler near main stairs is not working","location":"Block B","category":"Water"})
        assert r.status_code == 201, r.text
        issue = r.json()
        assert issue["status"] == "open"
        assert client.patch("/issues/"+issue["id"]+"/status", json={"status":"in_progress"}).status_code == 200
        assert client.get("/issues").json()["issues"][0]["status"] == "in_progress"

def test_duplicate_suggestion():
    with TestClient(app) as client:
        data={"title":"Water cooler broken","description":"Water cooler in block B not working","location":"Block B","category":"Water"}
        client.post("/issues",json=data)
        r=client.post("/issues",json=data)
        assert r.status_code == 201
        assert len(r.json()["possible_duplicates"]) >= 1

def test_websocket_event():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "connected"
            client.post("/issues",json={"title":"Lights not working","description":"Lights flickering in corridor","location":"Block A","category":"Electricity"})
            assert ws.receive_json()["type"] == "issue.created"

def test_invalid_status_rejected():
    with TestClient(app) as client:
        response = client.post("/issues", json={"title":"Leaking tap", "description":"Tap leaks in washroom", "location":"Block C", "category":"Water"})
        assert response.status_code == 201
        issue_id = response.json()["id"]
        bad = client.patch("/issues/"+issue_id+"/status", json={"status":"deleted"})
        assert bad.status_code == 422
        assert client.get("/issues").json()["issues"][0]["status"] == "open"

def test_missing_issue_returns_404():
    with TestClient(app) as client:
        response = client.patch("/issues/does-not-exist/status", json={"status":"resolved"})
        assert response.status_code == 404

def test_status_change_broadcasts_event():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "connected"
            created = client.post("/issues", json={"title":"Wifi outage", "description":"Network unavailable on floor two", "location":"Library", "category":"Internet"})
            assert created.status_code == 201
            assert ws.receive_json()["type"] == "issue.created"
            updated = client.patch("/issues/"+created.json()["id"]+"/status", json={"status":"resolved"})
            assert updated.status_code == 200
            event = ws.receive_json()
            assert event["type"] == "issue.updated"
            assert event["issue"]["status"] == "resolved"
