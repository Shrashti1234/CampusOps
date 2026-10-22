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
