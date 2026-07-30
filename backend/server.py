from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
import re
import uuid
import bcrypt
import jwt
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, Query, UploadFile, File, Header
from fastapi.responses import Response
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

# ---------------- Object Storage ----------------
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "teachhub"
_storage_key = None

ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_DOC = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"}
MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif",
    "webp": "image/webp", "pdf": "application/pdf", "txt": "text/plain", "csv": "text/csv",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    if resp.status_code == 403:
        globals()['_storage_key'] = None
        key = init_storage()
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 403:
        globals()['_storage_key'] = None
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ---------------- Models ----------------
SUBJECTS = ["mathematics", "physics", "chemistry", "literature", "history", "foreign_languages", "other"]
GRADES = ["1-4", "5-6", "7-8", "9-11", "university"]
POST_TYPES = ["html", "worksheet", "blog"]

class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=80)

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class FileRef(BaseModel):
    file_id: str
    url: str
    original_filename: str
    content_type: str = ""
    size: int = 0

class TaskInput(BaseModel):
    type: str = "html"
    title: str = Field(min_length=1, max_length=140)
    subject: str
    grade: str
    description: str = Field(default="", max_length=500)
    html_code: Optional[str] = Field(default=None, max_length=1_000_000)
    body: Optional[str] = Field(default=None, max_length=50_000)
    files: List[FileRef] = Field(default_factory=list)
    folder_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_draft: bool = False

class FolderInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    subject: Optional[str] = None

class ReportInput(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class UpdateAccountInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_file_id: Optional[str] = None
    hide_followers: Optional[bool] = None
    hide_following: Optional[bool] = None

# ---------------- Serializers ----------------
def avatar_url_for(u: dict) -> Optional[str]:
    fid = u.get("avatar_file_id")
    return f"/api/files/{fid}" if fid else None

def user_public(u: dict) -> dict:
    return {"id": str(u["_id"]) if "_id" in u else u.get("id"),
            "email": u["email"], "name": u["name"], "role": u["role"],
            "bio": u.get("bio", ""),
            "avatar_file_id": u.get("avatar_file_id"),
            "avatar_url": avatar_url_for(u),
            "hide_followers": u.get("hide_followers", False),
            "hide_following": u.get("hide_following", False),
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
        "type": t.get("type", "html"),
        "title": t["title"],
        "subject": t["subject"],
        "grade": t["grade"],
        "description": t.get("description", ""),
        "html_code": t.get("html_code", "") or "",
        "body": t.get("body", "") or "",
        "files": t.get("files", []),
        "folder_id": t.get("folder_id"),
        "tags": t.get("tags", []),
        "views": t.get("views", 0),
        "likes_count": t.get("likes_count", 0),
        "author_id": t.get("author_id"),
        "author_name": author["name"] if author else "Unknown",
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "is_draft": t.get("is_draft", False),
        "liked": liked,
        "favorited": favorited,
    }

def task_card(t: dict, author_name: str = "Unknown") -> dict:
    d = {k: t[k] for k in t if k not in ("html_code", "body", "_id")}
    d["id"] = str(t["_id"])
    d["type"] = t.get("type", "html")
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
WELCOME_BODY = """👋 Welcome to TeachHub!

This is your private welcome note (a draft — only you can see it). Here's how to get started and how to use AI tools to create great content.

━━━━━━━━━━━━━━━━━━━━━━
HOW TO USE TEACHHUB
━━━━━━━━━━━━━━━━━━━━━━
• Browse the feed and open any post to run it — no account needed.
• Publish 3 kinds of posts from the "Publish" button:
   1) Interactive — a single HTML file that plays inside a safe sandbox.
   2) Worksheet — downloadable images/documents (PDF, DOCX, XLSX, PPTX).
   3) Blog — text + images to share teaching experiences.
• Like ❤, Favorite ⭐, and Follow other teachers.
• Studio: organize your posts into folders and preview them.
• Drafts: tick "Save as draft" to keep a post private until you're ready.

━━━━━━━━━━━━━━━━━━━━━━
PROMPT FOR AI → INTERACTIVE HTML TASK
━━━━━━━━━━━━━━━━━━━━━━
Copy this into ChatGPT / Claude / Gemini and fill in the [brackets]:

"Create a SINGLE self-contained HTML file for an interactive [TOPIC] activity for [GRADE] students studying [SUBJECT]. Requirements:
- Put ALL code in ONE file: HTML, CSS and JavaScript together (inline <style> and <script>). Do NOT split into separate files and do NOT use any external files, frameworks or CDNs.
- It must run standalone inside a sandboxed iframe with no internet access.
- Include [N] questions/steps with instant visual feedback, a running score, and a friendly, colorful, accessible UI (large touch targets, good contrast).
- Add a 'Restart' button. Keep it mobile-friendly.
Return only the complete HTML file."

Tip: paste the returned code into Publish → Interactive → HTML Code, and use the live Preview.

━━━━━━━━━━━━━━━━━━━━━━
PROMPTS FOR AI → WORKSHEET (2 steps)
━━━━━━━━━━━━━━━━━━━━━━
Step 1 — generate the task/content:
"Act as a [SUBJECT] teacher. Create [N] [TOPIC] exercises for [GRADE] students, ordered from easy to hard. Include a separate answer key at the end. Keep the language clear and age-appropriate."

Step 2 — turn it into a printable worksheet:
"Using the exercises above, design a clean, printable ONE-PAGE worksheet. Include: a title, 'Name' and 'Date' fields at the top, numbered questions with enough blank space for students to write answers, simple black-on-white typography, and A4 layout. Provide it as either a print-ready HTML page or a description I can export to PDF."

Then upload your file(s) in Publish → Worksheet.

━━━━━━━━━━━━━━━━━━━━━━
ДОБРО ПОЖАЛОВАТЬ В TEACHHUB!
━━━━━━━━━━━━━━━━━━━━━━
Это ваша личная заметка-черновик (видите её только вы).

Как пользоваться:
• Листайте ленту и открывайте посты — регистрация не нужна.
• Публикуйте 3 типа постов: Интерактив (один HTML-файл), Рабочий лист (файлы для скачивания), Блог (текст + картинки).
• Ставьте лайки, добавляйте в избранное, подписывайтесь на учителей.
• Студия: раскладывайте посты по папкам. Черновики видны только вам.

Промпт для ИИ → интерактивный HTML:
"Создай ОДИН самодостаточный HTML-файл с интерактивным заданием по теме [ТЕМА] для [КЛАСС]. Весь код (HTML, CSS, JS) должен быть в одном файле (inline <style> и <script>), без внешних файлов и CDN. Работает автономно в песочнице. Добавь [N] вопросов с мгновенной обратной связью, счётом очков, яркий доступный интерфейс и кнопку 'Заново'. Верни только полный HTML."

Промпты для ИИ → рабочий лист (2 шага):
Шаг 1 (задание): "Ты учитель [ПРЕДМЕТ]. Составь [N] заданий по теме [ТЕМА] для [КЛАСС] от простого к сложному, с ответами в конце."
Шаг 2 (лист): "На основе заданий выше свёрстай аккуратный печатный рабочий лист на ОДНУ страницу: заголовок, поля 'Имя' и 'Дата', пронумерованные вопросы с местом для ответа, чёрно-белая типографика, формат A4. Дай готовую к печати HTML-страницу или описание для экспорта в PDF."

Happy teaching! 🎓"""

async def create_welcome_post(user_id: str):
    now = datetime.now(timezone.utc).isoformat()
    await db.tasks.insert_one({
        "type": "blog",
        "title": "👋 Welcome to TeachHub — Guide & AI Prompts",
        "subject": "other", "grade": "university",
        "description": "Your private starter guide: how to use TeachHub and prompts for generating tasks with AI.",
        "html_code": None, "body": WELCOME_BODY, "files": [],
        "folder_id": None, "tags": ["guide", "welcome"],
        "views": 0, "likes_count": 0, "is_draft": True,
        "author_id": user_id, "created_at": now, "updated_at": now,
    })

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
    await create_welcome_post(str(res.inserted_id))
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
    type: Optional[str] = None,
    author_id: Optional[str] = None,
):
    q: dict = {}
    if search:
        q["title"] = {"$regex": re.escape(search), "$options": "i"}
    if subject and subject in SUBJECTS:
        q["subject"] = subject
    if grade and grade in GRADES:
        q["grade"] = grade
    if type and type in POST_TYPES:
        q["type"] = type
    if author_id:
        q["author_id"] = author_id
    q["is_draft"] = {"$ne": True}
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
    current_user = await get_optional_user(request)
    if t.get("is_draft"):
        is_owner = current_user and (current_user["id"] == t.get("author_id") or current_user.get("role") == "admin")
        if not is_owner:
            raise HTTPException(status_code=404, detail="Task not found")
    await db.tasks.update_one({"_id": t["_id"]}, {"$inc": {"views": 1}})
    t["views"] = t.get("views", 0) + 1
    return await task_public(t, current_user)

def validate_and_build(body: TaskInput, user: dict) -> dict:
    if body.type not in POST_TYPES:
        raise HTTPException(status_code=400, detail="Invalid post type")
    if body.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail="Invalid subject")
    if body.grade not in GRADES:
        raise HTTPException(status_code=400, detail="Invalid grade")
    if body.type == "html":
        if not body.html_code or not body.html_code.strip():
            raise HTTPException(status_code=400, detail="HTML code is required for HTML tasks")
    elif body.type == "worksheet":
        if not body.files:
            raise HTTPException(status_code=400, detail="At least one file is required for worksheets")
    elif body.type == "blog":
        if not body.body or not body.body.strip():
            raise HTTPException(status_code=400, detail="Body text is required for blog posts")
    return {
        "type": body.type,
        "title": sanitize_text(body.title),
        "subject": body.subject,
        "grade": body.grade,
        "description": sanitize_text(body.description),
        "html_code": body.html_code if body.type == "html" else None,
        "body": sanitize_text(body.body) if body.type == "blog" else None,
        "files": [f.model_dump() for f in body.files] if body.type in ("worksheet", "blog") else [],
        "folder_id": body.folder_id or None,
        "tags": [sanitize_text(x) for x in body.tags if x.strip()][:10],
        "is_draft": bool(body.is_draft),
    }

@api_router.post("/tasks")
async def create_task(body: TaskInput, user: dict = Depends(get_current_user)):
    doc = validate_and_build(body, user)
    now = datetime.now(timezone.utc).isoformat()
    doc.update({"views": 0, "likes_count": 0, "author_id": user["id"],
                "created_at": now, "updated_at": now})
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
    update = validate_and_build(body, user)
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
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
    if body.bio is not None:
        update["bio"] = sanitize_text(body.bio)
    if body.avatar_file_id is not None:
        update["avatar_file_id"] = body.avatar_file_id or None
    if body.hide_followers is not None:
        update["hide_followers"] = bool(body.hide_followers)
    if body.hide_following is not None:
        update["hide_following"] = bool(body.hide_following)
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
    await db.folders.delete_many({"user_id": uid})
    await db.follows.delete_many({"follower_id": uid})
    await db.follows.delete_many({"following_id": uid})
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

# ---------------- File Upload / Serve ----------------
BACKEND_PUBLIC_URL = os.environ.get("BACKEND_PUBLIC_URL", "")

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin")
    if ext not in ALLOWED_IMAGE and ext not in ALLOWED_DOC:
        raise HTTPException(status_code=400, detail=f"File type .{ext} not allowed")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    content_type = MIME_TYPES.get(ext, file.content_type or "application/octet-stream")
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    file_id = str(uuid.uuid4())
    await db.files.insert_one({
        "id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "owner_id": user["id"],
        "is_image": ext in ALLOWED_IMAGE,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "file_id": file_id,
        "url": f"/api/files/{file_id}",
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "is_image": ext in ALLOWED_IMAGE,
    }

@api_router.get("/files/{file_id}")
async def serve_file(file_id: str, download: bool = False):
    record = await db.files.find_one({"id": file_id, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = get_object(record["storage_path"])
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{record["original_filename"]}"'
    return Response(content=data, media_type=record.get("content_type", content_type), headers=headers)

# ---------------- Folders ----------------
@api_router.get("/folders")
async def list_folders(user: dict = Depends(get_current_user)):
    folders = await db.folders.find({"user_id": user["id"]}).sort("created_at", 1).to_list(200)
    result = []
    for f in folders:
        result.append({
            "id": str(f["_id"]),
            "name": f["name"],
            "subject": f.get("subject"),
            "count": await db.tasks.count_documents({"author_id": user["id"], "folder_id": str(f["_id"])}),
        })
    return result

@api_router.post("/folders")
async def create_folder(body: FolderInput, user: dict = Depends(get_current_user)):
    doc = {"user_id": user["id"], "name": sanitize_text(body.name),
           "subject": body.subject if body.subject in SUBJECTS else None,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.folders.insert_one(doc)
    return {"id": str(res.inserted_id), "name": doc["name"], "subject": doc["subject"], "count": 0}

@api_router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
    f = await db.folders.find_one({"_id": ObjectId(folder_id)})
    if not f or f["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.folders.delete_one({"_id": f["_id"]})
    await db.tasks.update_many({"folder_id": folder_id}, {"$set": {"folder_id": None}})
    return {"message": "Folder deleted"}

# ---------------- Follows / Public Profiles ----------------
async def build_profile(u: dict, current_user: Optional[dict]) -> dict:
    uid = str(u["_id"])
    is_self = bool(current_user and current_user["id"] == uid)
    is_following = False
    if current_user and not is_self:
        is_following = await db.follows.find_one({"follower_id": current_user["id"], "following_id": uid}) is not None
    hide_followers = bool(u.get("hide_followers", False))
    hide_following = bool(u.get("hide_following", False))
    post_q = {"author_id": uid} if is_self else {"author_id": uid, "is_draft": {"$ne": True}}
    profile = {
        "id": uid, "name": u["name"], "role": u["role"], "created_at": u.get("created_at"),
        "bio": u.get("bio", ""),
        "avatar_file_id": u.get("avatar_file_id"),
        "avatar_url": avatar_url_for(u),
        "post_count": await db.tasks.count_documents(post_q),
        "is_following": is_following,
        "is_self": is_self,
        "hide_followers": hide_followers,
        "hide_following": hide_following,
    }
    if hide_followers and not is_self:
        profile["followers_count"] = None
    else:
        profile["followers_count"] = await db.follows.count_documents({"following_id": uid})
    if hide_following and not is_self:
        profile["following_count"] = None
    else:
        profile["following_count"] = await db.follows.count_documents({"follower_id": uid})
    return profile

@api_router.get("/users/{user_id}")
async def get_user_profile(user_id: str, request: Request):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    u = await db.users.find_one({"_id": ObjectId(user_id)})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    current_user = await get_optional_user(request)
    return await build_profile(u, current_user)

@api_router.get("/users/{user_id}/tasks")
async def user_tasks(user_id: str, page: int = Query(1, ge=1), limit: int = Query(12, ge=1, le=50)):
    q = {"author_id": user_id, "is_draft": {"$ne": True}}
    total = await db.tasks.count_documents(q)
    skip = (page - 1) * limit
    docs = await db.tasks.find(q).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    items = await enrich_cards(docs)
    return {"items": items, "total": total, "page": page, "pages": max(1, (total + limit - 1) // limit)}

@api_router.post("/users/{user_id}/follow")
async def toggle_follow(user_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    existing = await db.follows.find_one({"follower_id": user["id"], "following_id": user_id})
    if existing:
        await db.follows.delete_one({"_id": existing["_id"]})
        following = False
    else:
        await db.follows.insert_one({"follower_id": user["id"], "following_id": user_id,
                                     "created_at": datetime.now(timezone.utc).isoformat()})
        following = True
    return {"following": following, "followers_count": await db.follows.count_documents({"following_id": user_id})}

async def _follow_user_list(ids: list, current_user: Optional[dict]):
    result = []
    for uid in ids:
        if not ObjectId.is_valid(uid):
            continue
        u = await db.users.find_one({"_id": ObjectId(uid)})
        if not u:
            continue
        is_following = False
        if current_user:
            is_following = await db.follows.find_one({"follower_id": current_user["id"], "following_id": uid}) is not None
        result.append({"id": uid, "name": u["name"], "role": u["role"], "is_following": is_following,
                       "avatar_url": avatar_url_for(u), "avatar_file_id": u.get("avatar_file_id"),
                       "is_self": bool(current_user and current_user["id"] == uid)})
    return result

@api_router.get("/users/{user_id}/followers")
async def get_followers(user_id: str, request: Request):
    current_user = await get_optional_user(request)
    target = await db.users.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) else None
    is_self = bool(current_user and target and current_user["id"] == str(target["_id"]))
    if target and target.get("hide_followers") and not is_self:
        return []
    docs = await db.follows.find({"following_id": user_id}).to_list(1000)
    return await _follow_user_list([d["follower_id"] for d in docs], current_user)

@api_router.get("/users/{user_id}/following")
async def get_following(user_id: str, request: Request):
    current_user = await get_optional_user(request)
    target = await db.users.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) else None
    is_self = bool(current_user and target and current_user["id"] == str(target["_id"]))
    if target and target.get("hide_following") and not is_self:
        return []
    docs = await db.follows.find({"follower_id": user_id}).to_list(1000)
    return await _follow_user_list([d["following_id"] for d in docs], current_user)

@api_router.get("/feed/following")
async def following_feed(request: Request, page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50),
                         user: dict = Depends(get_current_user)):
    follows = await db.follows.find({"follower_id": user["id"]}).to_list(1000)
    author_ids = [f["following_id"] for f in follows]
    if not author_ids:
        return {"items": [], "total": 0, "page": page, "pages": 1}
    q = {"author_id": {"$in": author_ids}, "is_draft": {"$ne": True}}
    total = await db.tasks.count_documents(q)
    skip = (page - 1) * limit
    docs = await db.tasks.find(q).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    items = await enrich_cards(docs)
    return {"items": items, "total": total, "page": page, "pages": max(1, (total + limit - 1) // limit)}

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
    await db.follows.create_index([("follower_id", 1), ("following_id", 1)], unique=True)
    await db.tasks.create_index([("created_at", -1)])
    await db.tasks.create_index([("type", 1)])
    await db.files.create_index("id", unique=True)
    await seed_admin()
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
