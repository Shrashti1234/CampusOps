import os
import tempfile
from uuid import uuid4

temp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = "sqlite:///" + temp.name
os.environ["JWT_SECRET"] = "testing-only-not-for-production"

from fastapi.testclient import TestClient
from main import app, Session, User, password_hash
from datetime import datetime, timezone

def student(client):
    email = str(uuid4())+"@example.edu"
    response=client.post("/auth/register",json={"email":email,"password":"correct horse battery"})
    assert response.status_code==201,response.text
    return response.json()["access_token"]

def admin(client):
    email=str(uuid4())+"@example.edu"
    with Session() as db:
        u=User(id=str(uuid4()),email=email,password_hash=password_hash.hash("admin-test-password"),role="admin",created_at=datetime.now(timezone.utc))
        db.add(u);db.commit()
    response=client.post("/auth/login",json={"email":email,"password":"admin-test-password"})
    assert response.status_code==200
    return response.json()["access_token"]

def headers(token): return {"Authorization":"Bearer "+token}
def payload(): return {"title":"Broken water cooler","description":"Cooler near main stairs is not working","location":"Block B","category":"Water"}

def test_auth_required():
    with TestClient(app) as c:
        assert c.get("/issues").status_code==401
        assert c.post("/issues",json=payload()).status_code==401

def test_student_can_submit_but_cannot_change_status():
    with TestClient(app) as c:
        t=student(c)
        r=c.post("/issues",json=payload(),headers=headers(t))
        assert r.status_code==201,r.text
        issue_id=r.json()["id"]
        assert c.patch("/issues/"+issue_id+"/status",json={"status":"resolved"},headers=headers(t)).status_code==403
        assert c.get("/issues",headers=headers(t)).json()["issues"][0]["id"]==issue_id

def test_student_isolation():
    with TestClient(app) as c:
        t1=student(c);t2=student(c)
        c.post("/issues",json=payload(),headers=headers(t1))
        assert c.get("/issues",headers=headers(t2)).json()["issues"]==[]

def test_admin_can_manage_status():
    with TestClient(app) as c:
        t=student(c);a=admin(c)
        issue=c.post("/issues",json=payload(),headers=headers(t)).json()
        assert c.patch("/issues/"+issue["id"]+"/status",json={"status":"in_progress"},headers=headers(a)).status_code==200
        assert any(i["id"]==issue["id"] for i in c.get("/issues",headers=headers(a)).json()["issues"])

def test_duplicate_suggestion_own_issues_only():
    with TestClient(app) as c:
        t=student(c);other=student(c)
        c.post("/issues",json=payload(),headers=headers(other))
        first=c.post("/issues",json=payload(),headers=headers(t))
        assert first.json()["possible_duplicates"]==[]
        second=c.post("/issues",json=payload(),headers=headers(t))
        assert second.json()["possible_duplicates"]

def test_websocket_authenticated_and_private():
    with TestClient(app) as c:
        t1=student(c);t2=student(c)
        with c.websocket_connect("/ws") as ws:
            ws.send_text(t1)
            assert ws.receive_json()["type"]=="connected"
            c.post("/issues",json=payload(),headers=headers(t1))
            assert ws.receive_json()["type"]=="issue.created"
        with c.websocket_connect("/ws") as ws:
            ws.send_text(t2)
            assert ws.receive_json()["type"]=="connected"
            a=admin(c)
            c.post("/issues",json=payload(),headers=headers(t1))
            # Student 2 receives no event from student 1. Verify by a separate
            # event belonging to student 2, which must be the next received.
            c.post("/issues",json=payload(),headers=headers(t2))
            assert ws.receive_json()["issue"]["owner_id"]==c.get("/auth/me",headers=headers(t2)).json()["id"]

def test_invalid_status_and_missing_issue():
    with TestClient(app) as c:
        a=admin(c)
        assert c.patch("/issues/unknown/status",json={"status":"resolved"},headers=headers(a)).status_code==404
        assert c.patch("/issues/unknown/status",json={"status":"invalid"},headers=headers(a)).status_code==422

def test_bad_login():
    with TestClient(app) as c:
        t=student(c)
        assert c.post("/auth/login",json={"email":"missing@example.edu","password":"not-correct"}).status_code==401
