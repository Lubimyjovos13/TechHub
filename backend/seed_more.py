import asyncio, os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
def now(): return datetime.now(timezone.utc).isoformat()

SIMPLE = lambda title: f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{font-family:system-ui;padding:40px;text-align:center;background:#F8FAFC}}h1{{color:#0F172A}}button{{padding:12px 20px;font-size:18px;border:2px solid #0F172A;border-radius:8px;background:#BAE6FD;cursor:pointer;font-weight:700}}</style></head><body><h1>{title}</h1><button onclick="this.innerText=\'Well done! ✅\'">Click me</button></body></html>'

EXTRA = [
    ("Shakespeare Timeline", "literature", "9-11", "Interactive timeline of Shakespeare's major works."),
    ("French Vocabulary Match", "foreign_languages", "5-6", "Match French words to their English meanings."),
    ("World War II Map Quiz", "history", "9-11", "Identify key WWII locations on an interactive map."),
    ("Fraction Pizza", "mathematics", "1-4", "Learn fractions by slicing a virtual pizza."),
    ("Balancing Equations", "chemistry", "9-11", "Practice balancing chemical equations interactively."),
    ("Ohm's Law Calculator", "physics", "7-8", "Adjust voltage and resistance to see current change."),
    ("Grammar Detective", "foreign_languages", "7-8", "Find grammar mistakes in sample sentences."),
    ("Ancient Rome Explorer", "history", "5-6", "Click landmarks to learn about Ancient Rome."),
    ("Poetry Rhyme Builder", "literature", "5-6", "Build rhyming couplets in this creative exercise."),
    ("Geometry Angle Trainer", "mathematics", "7-8", "Estimate and measure angles interactively."),
]

async def main():
    t = await db.users.find_one({"email": "teacher@teachhub.com"})
    tid = str(t["_id"])
    for title, subject, grade, desc in EXTRA:
        if await db.tasks.find_one({"title": title}):
            continue
        await db.tasks.insert_one({"title": title, "subject": subject, "grade": grade, "description": desc, "html_code": SIMPLE(title), "tags": [subject], "views": 0, "likes_count": 0, "author_id": tid, "created_at": now(), "updated_at": now()})
    print("total tasks:", await db.tasks.count_documents({}))

asyncio.run(main())
