"""HTTP smoke test for a running local CampusOps stack (standard library only)."""
import json
import os
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
    assert request("/issues/similar", "POST", {
        "title": "Library wifi offline",
        "description": "Internet is unavailable in the reading room",
        "location": "Library",
        "category": "Internet"
    }, token=token)["possible_duplicates"]
    request("/issues/" + issue["id"] + "/status", "PATCH", {"status": "resolved"}, token=token, expected=403)
    print("PASS: health, auth, issue submission, analytics, duplicate preview, role restrictions")

if __name__ == "__main__":
    main()
