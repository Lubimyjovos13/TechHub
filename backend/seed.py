import asyncio, os
from dotenv import load_dotenv
from pathlib import Path
ROOT = Path(__file__).parent
load_dotenv(ROOT / '.env')
import bcrypt
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]

def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def now(): return datetime.now(timezone.utc).isoformat()

QUIZ = '''<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{font-family:system-ui,sans-serif;margin:0;padding:32px;background:#F8FAFC;color:#0F172A}.q{background:#fff;border:2px solid #0F172A;border-radius:12px;padding:24px;max-width:520px;margin:0 auto;box-shadow:6px 6px 0 #0F172A}h2{margin-top:0}button{display:block;width:100%;text-align:left;margin:8px 0;padding:12px 16px;font-size:16px;border:2px solid #0F172A;border-radius:8px;background:#fff;cursor:pointer;font-weight:600}button:hover{background:#BAE6FD}.ok{background:#A7F3D0!important}.bad{background:#FCA5A5!important}#s{font-size:20px;font-weight:800;margin-top:16px}</style></head><body><div class="q"><h2>Quick Math Quiz</h2><p id="p">Question 1: What is 7 × 8?</p><div id="opts"></div><div id="s"></div></div><script>const qs=[{q:"Question 1: What is 7 × 8?",o:["54","56","64","48"],a:1},{q:"Question 2: What is 12 + 15?",o:["27","25","28","26"],a:0},{q:"Question 3: What is 81 ÷ 9?",o:["8","7","9","6"],a:2}];let i=0,score=0;function render(){document.getElementById('p').innerText=qs[i].q;const c=document.getElementById('opts');c.innerHTML='';qs[i].o.forEach((t,idx)=>{const b=document.createElement('button');b.innerText=t;b.onclick=()=>pick(idx,b);c.appendChild(b);});}function pick(idx,b){if(idx===qs[i].a){b.className='ok';score++;}else{b.className='bad';}setTimeout(()=>{i++;if(i<qs.length)render();else finish();},600);}function finish(){document.getElementById('p').innerText='Done!';document.getElementById('opts').innerHTML='';document.getElementById('s').innerText='Score: '+score+' / '+qs.length+' 🎉';}render();</script></body></html>'''

DRAG = '''<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:system-ui,sans-serif;padding:32px;background:#F8FAFC;text-align:center}.box{display:inline-block;margin:10px;padding:20px 26px;border:2px solid #0F172A;border-radius:10px;background:#FDE047;font-size:22px;font-weight:800;cursor:grab;box-shadow:4px 4px 0 #0F172A}.slot{display:inline-block;width:90px;height:70px;margin:10px;border:2px dashed #0F172A;border-radius:10px;vertical-align:middle;line-height:70px;font-size:22px;background:#fff}h2{color:#0F172A}</style></head><body><h2>Drag numbers in ascending order</h2><div id="src"></div><hr style="margin:24px 0"><div id="slots"></div><script>const nums=[5,2,8,1];const src=document.getElementById('src');nums.forEach(n=>{const d=document.createElement('div');d.className='box';d.draggable=true;d.innerText=n;d.ondragstart=e=>e.dataTransfer.setData('t',n);src.appendChild(d);});const slots=document.getElementById('slots');[0,1,2,3].forEach(()=>{const s=document.createElement('div');s.className='slot';s.ondragover=e=>e.preventDefault();s.ondrop=e=>{e.preventDefault();s.innerText=e.dataTransfer.getData('t');};slots.appendChild(s);});</script></body></html>'''

PHYS = '''<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0F172A;overflow:hidden;font-family:system-ui}canvas{display:block}#t{position:fixed;top:12px;left:12px;color:#FDE047;font-weight:800}</style></head><body><div id="t">Click to launch a ball 🚀</div><canvas id="c"></canvas><script>const c=document.getElementById('c');c.width=innerWidth;c.height=innerHeight;const x=c.getContext('2d');let balls=[];c.onclick=e=>{balls.push({x:e.clientX,y:e.clientY,vx:(Math.random()-.5)*8,vy:-10,r:12+Math.random()*10,col:`hsl(${Math.random()*360},70%,60%)`});};function loop(){x.fillStyle='#0F172A';x.fillRect(0,0,c.width,c.height);balls.forEach(b=>{b.vy+=0.4;b.x+=b.vx;b.y+=b.vy;if(b.y+b.r>c.height){b.y=c.height-b.r;b.vy*=-0.75;}x.beginPath();x.arc(b.x,b.y,b.r,0,7);x.fillStyle=b.col;x.fill();x.strokeStyle='#fff';x.lineWidth=2;x.stroke();});requestAnimationFrame(loop);}loop();</script></body></html>'''

CHEM = '''<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:system-ui;padding:32px;background:#F8FAFC;text-align:center}.el{display:inline-block;width:80px;height:80px;margin:6px;border:2px solid #0F172A;border-radius:8px;background:#A7F3D0;font-weight:800;cursor:pointer;box-shadow:3px 3px 0 #0F172A}.el:hover{background:#7DD3FC}.sym{font-size:26px;display:block;margin-top:10px}.num{font-size:11px}#info{margin-top:20px;font-size:20px;font-weight:700;min-height:30px}</style></head><body><h2>Click an element</h2><div id="grid"></div><div id="info"></div><script>const els=[["H","Hydrogen",1],["He","Helium",2],["Li","Lithium",3],["C","Carbon",6],["N","Nitrogen",7],["O","Oxygen",8],["Na","Sodium",11],["Fe","Iron",26]];const g=document.getElementById('grid');els.forEach(([s,n,z])=>{const d=document.createElement('div');d.className='el';d.innerHTML=`<span class="num">${z}</span><span class="sym">${s}</span>`;d.onclick=()=>document.getElementById('info').innerText=`${s} = ${n} (Z=${z})`;g.appendChild(d);});</script></body></html>'''

TASKS = [
    ("Interactive Math Quiz", "mathematics", "5-6", "A quick 3-question multiplication and division quiz with instant feedback.", QUIZ, ["quiz","arithmetic","fun"]),
    ("Sort the Numbers (Drag & Drop)", "mathematics", "1-4", "Drag the numbers into ascending order. Great for early learners.", DRAG, ["drag-drop","ordering"]),
    ("Projectile Physics Sandbox", "physics", "9-11", "Click anywhere to launch balls and watch gravity and bouncing in action.", PHYS, ["simulation","gravity","canvas"]),
    ("Explore the Periodic Table", "chemistry", "7-8", "Click chemical elements to learn their names and atomic numbers.", CHEM, ["elements","interactive"]),
]

async def main():
    await db.users.create_index("email", unique=True)
    teacher = await db.users.find_one({"email": "teacher@teachhub.com"})
    if not teacher:
        res = await db.users.insert_one({"email":"teacher@teachhub.com","password_hash":hp("teacher12345"),"name":"Maria Ivanova","role":"teacher","created_at":now()})
        tid = str(res.inserted_id)
    else:
        tid = str(teacher["_id"])
    admin_email = os.environ.get("ADMIN_EMAIL","admin@teachhub.com").lower()
    if not await db.users.find_one({"email":admin_email}):
        await db.users.insert_one({"email":admin_email,"password_hash":hp(os.environ.get("ADMIN_PASSWORD","admin12345")),"name":"Admin","role":"admin","created_at":now()})

    if await db.tasks.count_documents({}) == 0:
        for title, subject, grade, desc, html, tags in TASKS:
            await db.tasks.insert_one({"title":title,"subject":subject,"grade":grade,"description":desc,"html_code":html,"tags":tags,"views":0,"likes_count":0,"author_id":tid,"created_at":now(),"updated_at":now()})
        print(f"Seeded {len(TASKS)} tasks")
    else:
        print("Tasks already exist, skipping")
    print("Done")

asyncio.run(main())
