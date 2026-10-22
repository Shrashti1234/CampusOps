"""CampusOps authenticated API. Local development only until deployment hardening."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import secrets
import asyncio

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from similarity import compare

URL = os.getenv("DATABASE_URL", "sqlite:///./campusops.db")
engine = create_engine(URL, connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {}, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
password_hash = PasswordHash.recommended()
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Ephemeral secret means sessions expire on restart in local demo mode.
    JWT_SECRET = secrets.token_urlsafe(48)
ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(12), nullable=False, default="student")
    created_at = Column(DateTime(timezone=True), nullable=False)

class Issue(Base):
    __tablename__ = "issues"
    id = Column(String(36), primary_key=True)
    title = Column(String(140), nullable=False)
    description = Column(String(1200), nullable=False)
    location = Column(String(100), nullable=False)
    category = Column(String(60), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    # Lightweight migration for existing local SQLite demo data.
    # For production use Alembic migrations instead.
    if URL.startswith("sqlite"):
        from sqlalchemy import inspect, text
        with engine.begin() as conn:
            if "owner_id" not in {c["name"] for c in inspect(conn).get_columns("issues")}:
                conn.execute(text("ALTER TABLE issues ADD COLUMN owner_id VARCHAR(36)"))
    yield

app = FastAPI(title="CampusOps API", version="0.3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET","POST","PATCH"], allow_headers=["Content-Type", "Authorization"])
clients: dict[WebSocket, str] = {}  # websocket -> JWT, revalidated for every broadcast
sequence = 0

class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: str
    password: str

class IssueIn(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    description: str = Field(min_length=8, max_length=1200)
    location: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=60)

class StatusIn(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved)$")

def user_json(user):
    return {"id": user.id, "email": user.email, "role": user.role}

def issue_json(x):
    return {"id":x.id,"title":x.title,"description":x.description,"location":x.location,"category":x.category,"status":x.status,"owner_id":x.owner_id,"created_at":x.created_at.isoformat()+("Z" if x.created_at.tzinfo is None else "")}

def token_for(user):
    return jwt.encode({"sub":user.id,"exp":datetime.now(timezone.utc)+timedelta(hours=8)}, JWT_SECRET, algorithm=ALGORITHM)

def get_user_by_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], options={"require":["exp","sub"]})
        user_id = payload["sub"]
    except (InvalidTokenError, KeyError, TypeError):
        return None
    with Session() as db:
        return db.get(User, user_id)

def current_user(auth: HTTPAuthorizationCredentials | None = Depends(bearer)):
    user = get_user_by_token(auth.credentials) if auth and auth.scheme.lower() == "bearer" else None
    if user is None: raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate":"Bearer"})
    return user

def require_admin(user: User = Depends(current_user)):
    if user.role != "admin": raise HTTPException(403, "Admin role required")
    return user

@app.post("/auth/register", status_code=201)
def register(data: RegisterIn):
    email = data.email.strip().lower()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(422, "Valid email required")
    with Session() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "Email already registered")
        user = User(id=str(uuid4()), email=email, password_hash=password_hash.hash(data.password), role="student", created_at=datetime.now(timezone.utc))
        db.add(user)
        try: db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(409, "Email already registered")
        return {"access_token":token_for(user), "token_type":"bearer", "user":user_json(user)}

@app.post("/auth/login")
def login(data: LoginIn):
    with Session() as db:
        user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
        if not user or not password_hash.verify(data.password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")
        return {"access_token":token_for(user), "token_type":"bearer", "user":user_json(user)}

@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user_json(user)

def similar_issues(title, description, location, existing):
    return compare(title, description, location, existing)


async def broadcast(event, owner_id):
    for ws, token in list(clients.items()):
        user = get_user_by_token(token)
        if user is None:
            clients.pop(ws, None)
            try: await ws.close(code=1008)
            except Exception: pass
            continue
        if user.role == "admin" or user.id == owner_id:
            try: await ws.send_json(event)
            except Exception: clients.pop(ws, None)

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/issues")
def list_issues(user: User = Depends(current_user)):
    with Session() as db:
        query = select(Issue).order_by(Issue.created_at.desc())
        if user.role != "admin": query = query.where(Issue.owner_id == user.id)
        return {"issues":[issue_json(i) for i in db.scalars(query).all()], "sequence":sequence}

@app.get("/analytics")
def analytics(user: User = Depends(current_user)):
    """Counts only issues visible to this user; no cross-student leakage."""
    with Session() as db:
        query = select(Issue)
        if user.role != "admin":
            query = query.where(Issue.owner_id == user.id)
        rows = db.scalars(query).all()
    statuses = {"open": 0, "in_progress": 0, "resolved": 0}
    categories = {}
    locations = {}
    daily = {}
    for item in rows:
        statuses[item.status] = statuses.get(item.status, 0) + 1
        categories[item.category] = categories.get(item.category, 0) + 1
        locations[item.location] = locations.get(item.location, 0) + 1
        day = item.created_at.date().isoformat()
        daily[day] = daily.get(day, 0) + 1
    total = len(rows)
    return {
        "total": total,
        "status": statuses,
        "resolution_rate": round(100 * statuses["resolved"] / total, 1) if total else 0,
        "categories": [{"name": name, "count": count} for name, count in sorted(categories.items(), key=lambda x: (-x[1], x[0]))],
        "locations": [{"name": name, "count": count} for name, count in sorted(locations.items(), key=lambda x: (-x[1], x[0]))[:5]],
        "daily": [{"date": day, "count": daily[day]} for day in sorted(daily)],
    }

@app.post("/issues/similar")
def preview_similar(data: IssueIn, user: User = Depends(current_user)):
    """Preview potential duplicates before submitting, scoped to user's own reports."""
    with Session() as db:
        prior = db.scalars(select(Issue).where(Issue.status != "resolved", Issue.owner_id == user.id)).all()
        matches, engine = similar_issues(data.title, data.description, data.location, prior)
        return {"possible_duplicates": matches, "similarity_engine": engine}

@app.post("/issues", status_code=201)
async def create_issue(data: IssueIn, user: User = Depends(current_user)):
    global sequence
    if any(not v.strip() for v in (data.title,data.description,data.location,data.category)):
        raise HTTPException(422,"Fields cannot be blank")
    with Session() as db:
        # Student submissions are checked only against their own existing reports;
        # no other student's complaint details are disclosed.
        prior = db.scalars(select(Issue).where(Issue.status!="resolved", Issue.owner_id==user.id)).all()
        duplicates, engine = similar_issues(data.title,data.description,data.location,prior)
        issue = Issue(id=str(uuid4()),title=data.title.strip(),description=data.description.strip(),location=data.location.strip(),category=data.category.strip(),status="open",owner_id=user.id,created_at=datetime.now(timezone.utc))
        db.add(issue);db.commit();result=issue_json(issue)
    sequence+=1
    await broadcast({"type":"issue.created","sequence":sequence,"issue":result},user.id)
    return {**result,"possible_duplicates":duplicates,"similarity_engine":engine}

@app.patch("/issues/{issue_id}/status")
async def update_status(issue_id:str, data:StatusIn, user: User = Depends(require_admin)):
    global sequence
    with Session() as db:
        issue=db.get(Issue,issue_id)
        if issue is None: raise HTTPException(404,"Issue not found")
        issue.status=data.status;db.commit();result=issue_json(issue)
    sequence+=1
    await broadcast({"type":"issue.updated","sequence":sequence,"issue":result},result["owner_id"])
    return result

@app.websocket("/ws")
async def events(ws:WebSocket):
    # Authenticate with first message rather than URL query parameter.
    await ws.accept()
    try:
        try:
            token = await asyncio.wait_for(ws.receive_text(), timeout=10)
        except asyncio.TimeoutError:
            await ws.close(code=1008)
            return
        user = get_user_by_token(token)
        if user is None:
            await ws.close(code=1008)
            return
        clients[ws] = token
        await ws.send_json({"type":"connected","sequence":sequence})
        while True:
            await ws.receive_text()
            if get_user_by_token(token) is None:
                await ws.close(code=1008)
                break
    except WebSocketDisconnect: pass
    finally: clients.pop(ws,None)
