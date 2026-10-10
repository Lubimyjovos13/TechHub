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
    pinned: Optional[bool] = None
    highlight_color: Optional[str] = None

class CommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class ForgotPasswordInput(BaseModel):
    email: EmailStr

class ResetPasswordInput(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class ErrorReportInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    url: Optional[str] = Field(default=None, max_length=500)

class ErrorStatusInput(BaseModel):
    status: str

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
        "pinned": t.get("pinned", False),
        "highlight_color": t.get("highlight_color"),
        "is_guide": t.get("is_guide", False),
        "liked": liked,
        "favorited": favorited,
    }

def task_card(t: dict, author_name: str = "Unknown") -> dict:
    d = {k: t[k] for k in t if k not in ("html_code", "body", "_id")}
    d["id"] = str(t["_id"])
    d["type"] = t.get("type", "html")
    d["pinned"] = t.get("pinned", False)
    d["highlight_color"] = t.get("highlight_color")
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
    guide = await db.tasks.find_one({"is_guide": True})
    if guide:
        exists = await db.favorites.find_one({"user_id": user_id, "task_id": str(guide["_id"])})
        if not exists:
            await db.favorites.insert_one({"user_id": user_id, "task_id": str(guide["_id"]),
                                           "created_at": datetime.now(timezone.utc).isoformat()})

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
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc).isoformat()}})
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
    cursor = db.tasks.find(q).sort([("pinned", -1), ("created_at", -1)]).skip(skip).limit(limit)
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
    return await task_public(t, current_user)

@api_router.post("/tasks/{task_id}/view")
async def increment_view(task_id: str):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    r = await db.tasks.update_one({"_id": ObjectId(task_id)}, {"$inc": {"views": 1}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}

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
    doc = {
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
    if user.get("role") == "admin":
        if body.pinned is not None:
            doc["pinned"] = bool(body.pinned)
        if body.highlight_color is not None:
            doc["highlight_color"] = body.highlight_color or None
    return doc

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
        uid = str(u["_id"])
        pub["drafts_count"] = await db.tasks.count_documents({"author_id": uid, "is_draft": True})
        pub["published_count"] = await db.tasks.count_documents({"author_id": uid, "is_draft": {"$ne": True}})
        pub["task_count"] = pub["drafts_count"] + pub["published_count"]
        pub["folders_count"] = await db.folders.count_documents({"user_id": uid})
        pub["last_login_at"] = u.get("last_login_at")
        pub["time_spent_seconds"] = u.get("time_spent_seconds", 0)
        pub["created_at"] = u.get("created_at")
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

# ---------------- Comments ----------------
@api_router.get("/tasks/{task_id}/comments")
async def list_comments(task_id: str):
    docs = await db.comments.find({"task_id": task_id}).sort("created_at", -1).to_list(500)
    out = []
    for c in docs:
        u = await db.users.find_one({"_id": ObjectId(c["user_id"])}) if ObjectId.is_valid(c["user_id"]) else None
        out.append({"id": str(c["_id"]), "task_id": c["task_id"], "user_id": c["user_id"],
                    "user_name": c.get("user_name", u["name"] if u else "User"),
                    "avatar_file_id": u.get("avatar_file_id") if u else None,
                    "body": c["body"], "created_at": c["created_at"]})
    return out

@api_router.post("/tasks/{task_id}/comments")
async def add_comment(task_id: str, body: CommentInput, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(task_id) or not await db.tasks.find_one({"_id": ObjectId(task_id)}):
        raise HTTPException(status_code=404, detail="Task not found")
    doc = {"task_id": task_id, "user_id": user["id"], "user_name": user["name"],
           "body": sanitize_text(body.body), "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.comments.insert_one(doc)
    return {"id": str(res.inserted_id), "task_id": task_id, "user_id": user["id"],
            "user_name": user["name"], "avatar_file_id": user.get("avatar_file_id"),
            "body": doc["body"], "created_at": doc["created_at"]}

@api_router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    c = await db.comments.find_one({"_id": ObjectId(comment_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    task = await db.tasks.find_one({"_id": ObjectId(c["task_id"])}) if ObjectId.is_valid(c["task_id"]) else None
    can = user["id"] == c["user_id"] or user["role"] == "admin" or (task and task.get("author_id") == user["id"])
    if not can:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.comments.delete_one({"_id": c["_id"]})
    return {"message": "Deleted"}

# ---------------- Error Reports ----------------
ERR_STATUSES = ["untouched", "in_progress", "fixed"]

@api_router.post("/error-reports")
async def create_error_report(body: ErrorReportInput, request: Request):
    cu = await get_optional_user(request)
    await db.error_reports.insert_one({
        "message": sanitize_text(body.message), "url": sanitize_text(body.url or ""),
        "user_id": cu["id"] if cu else None, "user_name": cu["name"] if cu else "Guest",
        "status": "untouched", "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Reported"}

@api_router.get("/admin/error-reports")
async def admin_error_reports(admin: dict = Depends(require_admin)):
    docs = await db.error_reports.find().sort("created_at", -1).to_list(1000)
    return [{"id": str(d["_id"]), "message": d["message"], "url": d.get("url", ""),
             "user_name": d.get("user_name", "Guest"), "status": d.get("status", "untouched"),
             "created_at": d["created_at"]} for d in docs]

@api_router.patch("/admin/error-reports/{rid}")
async def admin_error_status(rid: str, body: ErrorStatusInput, admin: dict = Depends(require_admin)):
    if body.status not in ERR_STATUSES or not ObjectId.is_valid(rid):
        raise HTTPException(status_code=400, detail="Invalid")
    await db.error_reports.update_one({"_id": ObjectId(rid)}, {"$set": {"status": body.status}})
    return {"message": "Updated"}

# ---------------- Admin: promote + heartbeat ----------------
@api_router.post("/admin/users/{user_id}/promote")
async def admin_promote(user_id: str, admin: dict = Depends(require_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": "admin"}})
    return {"message": "Promoted"}

@api_router.post("/users/me/ping")
async def heartbeat(user: dict = Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"time_spent_seconds": 60}})
    return {"ok": True}

# ---------------- Admin: Excel export ----------------
def _ws_write(ws, headers, rows):
    ws.append(headers)
    for r in rows:
        ws.append(r)

@api_router.get("/admin/export/excel")
async def export_excel(admin: dict = Depends(require_admin)):
    from openpyxl import Workbook
    import io
    wb = Workbook()
    users = await db.users.find().to_list(10000)
    folders_by_user = {}
    async for f in db.folders.find():
        folders_by_user[f["user_id"]] = folders_by_user.get(f["user_id"], 0) + 1
    ws1 = wb.active; ws1.title = "Users"
    urows = []
    for u in users:
        uid = str(u["_id"])
        drafts = await db.tasks.count_documents({"author_id": uid, "is_draft": True})
        pub = await db.tasks.count_documents({"author_id": uid, "is_draft": {"$ne": True}})
        urows.append([uid, u["name"], u["email"], u["role"], folders_by_user.get(uid, 0),
                      drafts, pub, u.get("time_spent_seconds", 0), u.get("created_at", ""), u.get("last_login_at", "")])
    _ws_write(ws1, ["ID","Name","Email","Role","Folders","Drafts","Published","TimeSpent(s)","Registered","LastLogin"], urows)

    def task_rows(docs):
        rows = []
        for t in docs:
            rows.append([str(t["_id"]), t.get("created_at",""), t.get("author_id",""), t.get("folder_id","") or "",
                         t.get("views",0), t.get("likes_count",0), t.get("subject",""), t.get("grade",""),
                         t.get("description",""), (t.get("html_code") or t.get("body") or ""),
                         ",".join(t.get("tags",[])), "draft" if t.get("is_draft") else "published"])
        return rows
    hdr = ["ID","Created","AuthorID","FolderID","Views","Likes","Subject","Grade","Description","Code/Body","Tags","Status"]
    for sheet, tp in [("Tasks(HTML)","html"), ("Worksheets","worksheet"), ("Blog Posts","blog")]:
        docs = await db.tasks.find({"type": tp}).to_list(10000)
        ws = wb.create_sheet(sheet)
        _ws_write(ws, hdr, task_rows(docs))
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return Response(content=buf.read(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="teachhub_analytics.xlsx"'})

# ---------------- Admin: DB export / import (merge) ----------------
EXPORT_COLLECTIONS = ["users","tasks","likes","favorites","follows","folders","reports","files","comments","error_reports"]

@api_router.get("/admin/export/db")
async def export_db(admin: dict = Depends(require_admin)):
    import json as _json
    dump = {}
    for col in EXPORT_COLLECTIONS:
        docs = await db[col].find().to_list(100000)
        for d in docs:
            d["_id"] = str(d["_id"])
        dump[col] = docs
    content = _json.dumps({"version": 1, "data": dump}, ensure_ascii=False).encode("utf-8")
    return Response(content=content, media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="teachhub_db.json"'})

@api_router.post("/admin/import/db")
async def import_db(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    import json as _json
    raw = await file.read()
    try:
        payload = _json.loads(raw)
        data = payload.get("data", {})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid backup file")
    inserted = {}
    for col, docs in data.items():
        if col not in EXPORT_COLLECTIONS:
            continue
        count = 0
        for d in docs:
            _id = d.pop("_id", None)
            query = {"_id": ObjectId(_id)} if _id and ObjectId.is_valid(_id) else None
            if query and await db[col].find_one(query):
                continue
            if query:
                d["_id"] = ObjectId(_id)
            await db[col].insert_one(d)
            count += 1
        inserted[col] = count
    return {"message": "Imported (merge)", "inserted": inserted}

# ---------------- Password reset (Resend email) ----------------
import secrets as _secrets
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

import re as _re
import ipaddress as _ipaddress
from html.parser import HTMLParser as _HTMLParser
from urllib.parse import urlparse as _urlparse
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = _re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", _re.I)

def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        _ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)

def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)

class _EmailScan(_HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []
    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []
    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []

def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = _urlparse(low).hostname or ""
        if not _host_ok(host) or _urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = _urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")

async def _send_email(to: str, subject: str, html: str):
    _assert_safe_email(subject, html)
    import httpx as _httpx
    payload = {"to": [to], "subject": subject, "html": html, "from_name": os.environ["EMAIL_FROM_NAME"]}
    try:
        async with _httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                             headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
        r.raise_for_status()
        return r.json().get("id")
    except _httpx.HTTPStatusError as e:
        logger.error(f"email send failed: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Failed to send email")
    except Exception as e:
        logger.error(f"email send failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to send email")

@api_router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordInput):
    user = await db.users.find_one({"email": body.email.lower()})
    if user:
        token = _secrets.token_urlsafe(32)
        await db.reset_tokens.insert_one({
            "token": token, "user_id": str(user["_id"]), "used": False,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        base = os.environ["APP_BASE_URL"].rstrip("/")
        link = f"{base}/reset-password?token={token}"
        html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
                f'<h2>Reset your TeachHub password</h2>'
                f'<p>We received a request to reset your password. This link is valid for 1 hour:</p>'
                f'<p><a href="{link}" style="background:#FDE047;border:2px solid #0F172A;padding:10px 18px;'
                f'border-radius:8px;color:#0F172A;text-decoration:none;font-weight:bold">Reset password</a></p>'
                f'<p>If you did not request this, you can ignore this email.</p>'
                f'<p style="font-size:12px;color:#888">Sent by TeachHub. We never ask for your password by email.</p>'
                f'</td></tr></table>')
        import asyncio as _asyncio
        async def _bg():
            try:
                await _send_email(user["email"], "Reset your TeachHub password", html)
            except Exception as e:
                logger.error(f"reset email bg failed: {e}")
        _asyncio.create_task(_bg())
    return {"message": "If an account exists, a reset link has been sent."}

@api_router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordInput):
    rec = await db.reset_tokens.find_one({"token": body.token, "used": False})
    if not rec or rec["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    await db.users.update_one({"_id": ObjectId(rec["user_id"])},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    await db.reset_tokens.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    return {"message": "Password updated. You can now log in."}

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

async def seed_guide():
    if await db.tasks.find_one({"is_guide": True}):
        return
    admin = await db.users.find_one({"email": os.environ.get("ADMIN_EMAIL", "admin@teachhub.com").lower()})
    if not admin:
        return
    now = datetime.now(timezone.utc).isoformat()
    body = (
        "👋 Welcome to TeachHub!\n\nThis guide is auto-added to your Favorites. Here's how to use the platform and how to use AI to create content.\n\n"
        "HOW TO USE\n• Browse the feed and open any post to run it — no account needed.\n• Publish 3 kinds: Interactive (single HTML file), Worksheet (downloadable files), Blog (text + images).\n• Like, Favorite and Follow teachers. Use the Studio to organize posts into folders. Drafts stay private.\n\n"
        "PROMPT → INTERACTIVE HTML\n\"Create a SINGLE self-contained HTML file for an interactive [TOPIC] activity for [GRADE] in [SUBJECT]. Put ALL HTML, CSS and JavaScript in ONE file (inline <style> and <script>), no external files or CDNs. It must run inside a sandboxed iframe. Include [N] questions with instant feedback, a score, a Restart button and a colorful accessible mobile-friendly UI. Return only the HTML file.\"\n\n"
        "PROMPTS → WORKSHEET (2 steps)\nStep 1 (task): \"Act as a [SUBJECT] teacher. Create [N] [TOPIC] exercises for [GRADE], easy to hard, with an answer key.\"\nStep 2 (worksheet): \"Turn the exercises above into a clean printable one-page worksheet: title, Name/Date fields, numbered questions with space to write, black-on-white A4. Give print-ready HTML or a PDF-export description.\"\n\n"
        "━━━━━━━━━━\nДОБРО ПОЖАЛОВАТЬ!\n• Публикуйте 3 типа постов: Интерактив, Рабочий лист, Блог.\n• Лайки, избранное, подписки; Студия для папок; черновики видны только вам.\n\nПромпт → интерактивный HTML: \"Создай ОДИН HTML-файл с заданием по теме [ТЕМА] для [КЛАСС]. Весь код (HTML, CSS, JS) в одном файле, без внешних файлов/CDN. Работает в песочнице. [N] вопросов, мгновенная обратная связь, счёт, кнопка 'Заново'. Верни только HTML.\"\nПромпты → рабочий лист: Шаг 1: \"Составь [N] заданий по теме [ТЕМА] для [КЛАСС] с ответами.\" Шаг 2: \"Свёрстай печатный лист на одну страницу: заголовок, Имя/Дата, пронумерованные вопросы, A4.\"\n\nHappy teaching! 🎓"
    )
    await db.tasks.insert_one({
        "type": "blog", "title": "📘 TeachHub Guide & AI Prompts", "subject": "other", "grade": "university",
        "description": "How to use TeachHub and prompts for generating interactive tasks and worksheets with AI.",
        "html_code": None, "body": body, "files": [], "folder_id": None, "tags": ["guide"],
        "views": 0, "likes_count": 0, "is_draft": False, "is_guide": True, "pinned": True,
        "highlight_color": "#FDE68A", "author_id": str(admin["_id"]), "created_at": now, "updated_at": now,
    })

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
    await seed_guide()
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
