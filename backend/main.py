"""CampusOps local MVP: demo only, no authentication or tenant isolation."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, DateTime, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

URL = os.getenv("DATABASE_URL", "sqlite:///./campusops.db")
engine = create_engine(URL, connect_args={"check_same_thread":False} if URL.startswith("sqlite") else {}, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

class Base(DeclarativeBase): pass
class Issue(Base):
    __tablename__ = "issues"
    id = Column(String(36), primary_key=True)
    title = Column(String(140), nullable=False)
    description = Column(String(1200), nullable=False)
    location = Column(String(100), nullable=False)
    category = Column(String(60), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), nullable=False)

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="CampusOps API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET","POST","PATCH"], allow_headers=["Content-Type"])
clients: set[WebSocket] = set()
sequence = 0

class IssueIn(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    description: str = Field(min_length=8, max_length=1200)
    location: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=60)

class StatusIn(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved)$")

def as_json(x):
    return {"id":x.id,"title":x.title,"description":x.description,"location":x.location,"category":x.category,"status":x.status,"created_at":x.created_at.isoformat()+("Z" if x.created_at.tzinfo is None else "")}

def similar_issues(title, description, location, existing):
    if not existing: return []
    documents = [title+" "+description+" "+location] + [i.title+" "+i.description+" "+i.location for i in existing]
    vectors = TfidfVectorizer(stop_words="english", ngram_range=(1,2)).fit_transform(documents)
    scores = cosine_similarity(vectors[0:1], vectors[1:]).ravel()
    return [{"id":i.id,"title":i.title,"similarity":round(float(score),3)} for i,score in sorted(zip(existing,scores), key=lambda x:x[1],reverse=True) if score>=0.25][:3]

async def broadcast(event):
    for ws in list(clients):
        try: await ws.send_json(event)
        except Exception: clients.discard(ws)

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/issues")
def list_issues():
    with Session() as db:
        return {"issues":[as_json(i) for i in db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()], "sequence":sequence}

@app.post("/issues", status_code=201)
async def create_issue(data: IssueIn):
    global sequence
    if any(not value.strip() for value in (data.title,data.description,data.location,data.category)):
        raise HTTPException(422,"Fields cannot be blank")
    with Session() as db:
        previous=db.scalars(select(Issue).where(Issue.status!="resolved")).all()
        duplicates=similar_issues(data.title,data.description,data.location,previous)
        issue=Issue(id=str(uuid4()),title=data.title.strip(),description=data.description.strip(),location=data.location.strip(),category=data.category.strip(),status="open",created_at=datetime.now(timezone.utc))
        db.add(issue);db.commit();result=as_json(issue)
    sequence+=1
    await broadcast({"type":"issue.created","sequence":sequence,"issue":result,"possible_duplicates":duplicates})
    return {**result,"possible_duplicates":duplicates}

@app.patch("/issues/{issue_id}/status")
async def update_status(issue_id:str, data:StatusIn):
    global sequence
    with Session() as db:
        issue=db.get(Issue,issue_id)
        if issue is None: raise HTTPException(404,"Issue not found")
        issue.status=data.status;db.commit();result=as_json(issue)
    sequence+=1
    await broadcast({"type":"issue.updated","sequence":sequence,"issue":result})
    return result

@app.websocket("/ws")
async def events(ws:WebSocket):
    await ws.accept();clients.add(ws)
    try:
        await ws.send_json({"type":"connected","sequence":sequence})
        while True: await ws.receive_text()
    except WebSocketDisconnect: pass
    finally: clients.discard(ws)
