from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
import re
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, BeforeValidator, ConfigDict
from bson import ObjectId

# ---------------- DB ----------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# ---------------- App ----------------
app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- Auth utils ----------------
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def sanitize_text(value: str) -> str:
    # strip html tags from plain-text fields (title/description/tags)
    cleaned = re.sub(r"<[^>]*>", "", value or "")
    return cleaned.strip()

# ---------------- Models ----------------
SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"]
GRADES = ["1-4", "5-6", "7-8", "9-11", "university"]

class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=80)

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    subject: str
    grade: str
    description: str = Field(default="", max_length=500)
    html_code: str = Field(min_length=1, max_length=1_000_000)
    tags: List[str] = Field(default_factory=list)

class ReportInput(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class UpdateAccountInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    email: Optional[EmailStr] = None

# ---------------- Serializers ----------------
def user_public(u: dict) -> dict:
    return {"id": str(u["_id"]) if "_id" in u else u.get("id"),
            "email": u["email"], "name": u["name"], "role": u["role"],
            "created_at": u.get("created_at")}

async def task_public(t: dict, current_user: Optional[dict] = None) -> dict:
    tid = str(t["_id"])
    author = await db.users.find_one({"_id": ObjectId(t["author_id"])}) if t.get("author_id") else None
    liked = False
    favorited = False
    if current_user:
        uid = current_user["id"]
        liked = await db.likes.find_one({"user_id": uid, "task_id": tid}) is not None
        favorited = await db.favorites.find_one({"user_id": uid, "task_id": tid}) is not None
    return {
        "id": tid,
        "title": t["title"],
        "subject": t["subject"],
        "grade": t["grade"],
        "description": t.get("description", ""),
        "html_code": t.get("html_code", ""),
        "tags": t.get("tags", []),
        "views": t.get("views", 0),
        "likes_count": t.get("likes_count", 0),
        "author_id": t.get("author_id"),
        "author_name": author["name"] if author else "Unknown",
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "liked": liked,
        "favorited": favorited,
    }

def task_card(t: dict, author_name: str = "Unknown") -> dict:
    d = {k: t[k] for k in t if k != "html_code" and k != "_id"}
    d["id"] = str(t["_id"])
    d["author_name"] = author_name
    return d

async def enrich_cards(tasks: list) -> list:
    author_ids = {t["author_id"] for t in tasks if t.get("author_id") and ObjectId.is_valid(t["author_id"])}
    authors = {}
    if author_ids:
        cursor = db.users.find({"_id": {"$in": [ObjectId(a) for a in author_ids]}})
        async for u in cursor:
            authors[str(u["_id"])] = u["name"]
    return [task_card(t, authors.get(t.get("author_id"), "Unknown")) for t in tasks]

# ---------------- Auth Endpoints ----------------
@api_router.post("/auth/register")
async def register(body: RegisterInput):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": sanitize_text(body.name), "role": "teacher",
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    token = create_access_token(str(res.inserted_id), email)
    return {"token": token, "user": user_public(doc)}

@api_router.post("/auth/login")
async def login(body: LoginInput):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]), email)
    return {"token": token, "user": user_public(user)}

@api_router.post("/auth/logout")
async def logout():
    return {"message": "Logged out"}

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user_public({**user, "_id": user["id"]})

# ---------------- Task Endpoints ----------------
@api_router.get("/tasks")
async def list_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
):
    current_user = await get_optional_user(request)
    q: dict = {}
    if search:
        q["title"] = {"$regex": re.escape(search), "$options": "i"}
    if subject and subject in SUBJECTS:
        q["subject"] = subject
    if grade and grade in GRADES:
        q["grade"] = grade
    total = await db.tasks.count_documents(q)
    skip = (page - 1) * limit
    cursor = db.tasks.find(q).sort("created_at", -1).skip(skip).limit(limit)
    docs = [t async for t in cursor]
    items = await enrich_cards(docs)
    return {"items": items, "total": total, "page": page, "limit": limit,
            "pages": max(1, (total + limit - 1) // limit)}

@api_router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    t = await db.tasks.find_one({"_id": ObjectId(task_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.tasks.update_one({"_id": t["_id"]}, {"$inc": {"views": 1}})
    t["views"] = t.get("views", 0) + 1
    current_user = await get_optional_user(request)
    return await task_public(t, current_user)

@api_router.post("/tasks")
async def create_task(body: TaskInput, user: dict = Depends(get_current_user)):
    if body.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail="Invalid subject")
    if body.grade not in GRADES:
        raise HTTPException(status_code=400, detail="Invalid grade")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "title": sanitize_text(body.title),
        "subject": body.subject,
        "grade": body.grade,
        "description": sanitize_text(body.description),
        "html_code": body.html_code,
        "tags": [sanitize_text(x) for x in body.tags if x.strip()][:10],
        "views": 0, "likes_count": 0,
        "author_id": user["id"],
        "created_at": now, "updated_at": now,
    }
    res = await db.tasks.insert_one(doc)
    doc["_id"] = res.inserted_id
    return await task_public(doc, user)

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, body: TaskInput, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    t = await db.tasks.find_one({"_id": ObjectId(task_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if t["author_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    if body.subject not in SUBJECTS or body.grade not in GRADES:
        raise HTTPException(status_code=400, detail="Invalid subject or grade")
    update = {
        "title": sanitize_text(body.title),
        "subject": body.subject, "grade": body.grade,
        "description": sanitize_text(body.description),
        "html_code": body.html_code,
        "tags": [sanitize_text(x) for x in body.tags if x.strip()][:10],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tasks.update_one({"_id": t["_id"]}, {"$set": update})
    t.update(update)
    return await task_public(t, user)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    t = await db.tasks.find_one({"_id": ObjectId(task_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if t["author_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.tasks.delete_one({"_id": t["_id"]})
    await db.likes.delete_many({"task_id": task_id})
    await db.favorites.delete_many({"task_id": task_id})
    await db.reports.delete_many({"task_id": task_id})
    return {"message": "Deleted"}

@api_router.post("/tasks/{task_id}/like")
async def toggle_like(task_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    t = await db.tasks.find_one({"_id": ObjectId(task_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    existing = await db.likes.find_one({"user_id": user["id"], "task_id": task_id})
    if existing:
        await db.likes.delete_one({"_id": existing["_id"]})
        await db.tasks.update_one({"_id": t["_id"]}, {"$inc": {"likes_count": -1}})
        liked = False
    else:
        await db.likes.insert_one({"user_id": user["id"], "task_id": task_id,
                                   "created_at": datetime.now(timezone.utc).isoformat()})
        await db.tasks.update_one({"_id": t["_id"]}, {"$inc": {"likes_count": 1}})
        liked = True
    updated = await db.tasks.find_one({"_id": t["_id"]})
    return {"liked": liked, "likes_count": updated.get("likes_count", 0)}

@api_router.post("/tasks/{task_id}/favorite")
async def toggle_favorite(task_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    if not await db.tasks.find_one({"_id": ObjectId(task_id)}):
        raise HTTPException(status_code=404, detail="Task not found")
    existing = await db.favorites.find_one({"user_id": user["id"], "task_id": task_id})
    if existing:
        await db.favorites.delete_one({"_id": existing["_id"]})
        return {"favorited": False}
    await db.favorites.insert_one({"user_id": user["id"], "task_id": task_id,
                                   "created_at": datetime.now(timezone.utc).isoformat()})
    return {"favorited": True}

@api_router.post("/tasks/{task_id}/report")
async def report_task(task_id: str, body: ReportInput, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    if not await db.tasks.find_one({"_id": ObjectId(task_id)}):
        raise HTTPException(status_code=404, detail="Task not found")
    await db.reports.insert_one({
        "task_id": task_id, "reporter_id": user["id"],
        "reason": sanitize_text(body.reason),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Reported"}

# ---------------- User Endpoints ----------------
@api_router.get("/users/me/tasks")
async def my_tasks(user: dict = Depends(get_current_user)):
    cursor = db.tasks.find({"author_id": user["id"]}).sort("created_at", -1)
    docs = [t async for t in cursor]
    return await enrich_cards(docs)

@api_router.get("/users/me/favorites")
async def my_favorites(user: dict = Depends(get_current_user)):
    favs = await db.favorites.find({"user_id": user["id"]}).sort("created_at", -1).to_list(500)
    ids = [ObjectId(f["task_id"]) for f in favs if ObjectId.is_valid(f["task_id"])]
    tasks = await db.tasks.find({"_id": {"$in": ids}}).to_list(500)
    order = {str(oid): i for i, oid in enumerate(ids)}
    tasks.sort(key=lambda t: order.get(str(t["_id"]), 0))
    return await enrich_cards(tasks)

@api_router.put("/users/me")
async def update_account(body: UpdateAccountInput, user: dict = Depends(get_current_user)):
    update = {}
    if body.name is not None:
        update["name"] = sanitize_text(body.name)
    if body.email is not None:
        new_email = body.email.lower()
        other = await db.users.find_one({"email": new_email})
        if other and str(other["_id"]) != user["id"]:
            raise HTTPException(status_code=400, detail="Email already in use")
        update["email"] = new_email
    if update:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    updated = await db.users.find_one({"_id": ObjectId(user["id"])})
    return user_public(updated)

@api_router.put("/users/me/password")
async def change_password(body: ChangePasswordInput, user: dict = Depends(get_current_user)):
    full = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not verify_password(body.current_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one({"_id": full["_id"]},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    return {"message": "Password updated"}

@api_router.delete("/users/me")
async def delete_account(user: dict = Depends(get_current_user)):
    uid = user["id"]
    await db.tasks.delete_many({"author_id": uid})
    await db.likes.delete_many({"user_id": uid})
    await db.favorites.delete_many({"user_id": uid})
    await db.users.delete_one({"_id": ObjectId(uid)})
    return {"message": "Account deleted"}

# ---------------- Admin Endpoints ----------------
@api_router.get("/admin/users")
async def admin_users(admin: dict = Depends(require_admin)):
    users = await db.users.find().sort("created_at", -1).to_list(1000)
    result = []
    for u in users:
        pub = user_public(u)
        pub["task_count"] = await db.tasks.count_documents({"author_id": str(u["_id"])})
        result.append(pub)
    return result

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.tasks.delete_many({"author_id": user_id})
    await db.likes.delete_many({"user_id": user_id})
    await db.favorites.delete_many({"user_id": user_id})
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted"}

@api_router.get("/admin/reports")
async def admin_reports(admin: dict = Depends(require_admin)):
    reports = await db.reports.find().sort("created_at", -1).to_list(1000)
    result = []
    for r in reports:
        task = None
        if ObjectId.is_valid(r["task_id"]):
            t = await db.tasks.find_one({"_id": ObjectId(r["task_id"])})
            if t:
                task = {"id": str(t["_id"]), "title": t["title"], "author_id": t.get("author_id")}
        reporter = await db.users.find_one({"_id": ObjectId(r["reporter_id"])}) if ObjectId.is_valid(r["reporter_id"]) else None
        result.append({
            "id": str(r["_id"]),
            "task_id": r["task_id"],
            "task": task,
            "reason": r["reason"],
            "reporter_name": reporter["name"] if reporter else "Unknown",
            "created_at": r["created_at"],
        })
    return result

@api_router.delete("/admin/reports/{report_id}")
async def admin_dismiss_report(report_id: str, admin: dict = Depends(require_admin)):
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    await db.reports.delete_one({"_id": ObjectId(report_id)})
    return {"message": "Report dismissed"}

@api_router.get("/admin/stats")
async def admin_stats(admin: dict = Depends(require_admin)):
    return {
        "users": await db.users.count_documents({}),
        "tasks": await db.tasks.count_documents({}),
        "reports": await db.reports.count_documents({}),
    }

@api_router.get("/")
async def root():
    return {"message": "TeachHub API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Startup ----------------
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@teachhub.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin12345")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "email": admin_email, "password_hash": hash_password(admin_password),
            "name": "Admin", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin seeded")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_password)}})

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.likes.create_index([("user_id", 1), ("task_id", 1)], unique=True)
    await db.favorites.create_index([("user_id", 1), ("task_id", 1)], unique=True)
    await db.tasks.create_index([("created_at", -1)])
    await seed_admin()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
