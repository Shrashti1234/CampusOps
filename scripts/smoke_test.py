"""HTTP smoke test for a running local CampusOps stack (standard library only)."""
import json
import os
import secrets
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

API = os.environ.get("CAMPUSOPS_API_URL", "http://127.0.0.1:8000")

def request(path, method="GET", payload=None, token=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(API + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            status = response.status
            body = json.load(response)
    except HTTPError as exc:
        status = exc.code
        body = json.loads(exc.read())
    assert status == expected, f"{method} {path}: expected {expected}, got {status}: {body}"
    return body

def main():
    if os.environ.get("CAMPUSOPS_SMOKE_CREATE_ADMIN") == "1":
        admin_email = "smoke-admin-" + str(uuid4()) + "@example.edu"
        admin_password = secrets.token_urlsafe(24)
        # Admin provisioning is a local-only CLI operation, not a public API.
        subprocess.run(
            ["docker", "compose", "exec", "-T", "backend",
             "python", "create_admin.py", admin_email],
            input=admin_password + "\n", text=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        os.environ["CAMPUSOPS_SMOKE_ADMIN_EMAIL"] = admin_email
        os.environ["CAMPUSOPS_SMOKE_ADMIN_PASSWORD"] = admin_password
    assert request("/health")["status"] == "ok"
    email = "smoke-" + str(uuid4()) + "@example.edu"
    credentials = {"email": email, "password": "demo-test-password-only"}
    registered = request("/auth/register", "POST", credentials, expected=201)
    token = registered["access_token"]
    assert registered["user"]["role"] == "student"
    assert request("/auth/login", "POST", credentials)["access_token"]
    assert request("/issues", expected=401)
    issue = request("/issues", "POST", {
        "title": "Library wifi offline",
        "description": "Internet is unavailable in the reading room",
        "location": "Library",
        "category": "Internet"
    }, token=token, expected=201)
    assert issue["status"] == "open"
    assert any(i["id"] == issue["id"] for i in request("/issues", token=token)["issues"])
    assert request("/analytics", token=token)["total"] >= 1
    second_email = "smoke-second-" + str(uuid4()) + "@example.edu"
    second = request("/auth/register", "POST", {
        "email": second_email, "password": "second-demo-test-password"
    }, expected=201)["access_token"]
    assert all(i["id"] != issue["id"] for i in request("/issues", token=second)["issues"])
    assert request("/analytics", token=second)["total"] == 0
    assert request("/issues/similar", "POST", {
        "title": "Library wifi offline",
        "description": "Internet is unavailable in the reading room",
        "location": "Library",
        "category": "Internet"
    }, token=token)["possible_duplicates"]
    request("/issues/" + issue["id"] + "/status", "PATCH", {"status": "resolved"}, token=token, expected=403)
    admin_email = os.environ.get("CAMPUSOPS_SMOKE_ADMIN_EMAIL")
    admin_password = os.environ.get("CAMPUSOPS_SMOKE_ADMIN_PASSWORD")
    if admin_email and admin_password:
        admin_token = request("/auth/login", "POST", {
            "email": admin_email, "password": admin_password
        })["access_token"]
        admin_issues = request("/issues", token=admin_token)["issues"]
        assert any(i["id"] == issue["id"] for i in admin_issues)
        changed = request("/issues/" + issue["id"] + "/status", "PATCH",
                          {"status": "resolved"}, token=admin_token)
        assert changed["status"] == "resolved"
        own_issues = request("/issues", token=token)["issues"]
        assert any(i["id"] == issue["id"] and i["status"] == "resolved" for i in own_issues)
        print("PASS: administrator visibility, status update, student status sync")
    print("PASS: health, auth, issue submission, analytics, duplicate preview, role restrictions")

if __name__ == "__main__":
    main()
