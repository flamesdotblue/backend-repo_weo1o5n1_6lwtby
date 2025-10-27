from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any
from difflib import SequenceMatcher
import io
import csv

from schemas import EvaluateRequest, EvaluateResponse, DiffItem, Bookmark, Progress, ExportRequest, ChatRequest
from database import create_document, get_documents, get_collection

app = FastAPI(title="Gita Pronunciation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample lightweight dataset for demo
CHAPTERS = [
    {"id": 1, "name": "Arjuna’s Dilemma"},
    {"id": 2, "name": "The Yoga of Knowledge"},
    {"id": 3, "name": "The Yoga of Action"},
]

VERSES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "id": 1,
            "sa": "धृतराष्ट्र उवाच | धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः |",
            "tr": "dhṛtarāśtra uvāca | dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
            "en": "Dhritarashtra said: At Kurukshetra, the field of Dharma, assembled for battle...",
        },
        {
            "id": 2,
            "sa": "पश्यैतां पाण्डुपुत्राणामाचार्य महतीं चमूम् |",
            "tr": "paśyaitāṁ pāṇḍu-putrāṇām ācārya mahatīṁ camūm |",
            "en": "Behold, O teacher, this mighty army of the sons of Pandu...",
        },
    ],
    2: [
        {
            "id": 11,
            "sa": "अशोच्यानन्वशोचस्त्वं प्रज्ञावादांश्च भाषसे |",
            "tr": "aśocyān anvaśocas tvaṁ prajñā-vādāṁś ca bhāṣase |",
            "en": "You grieve for those who should not be grieved for, yet speak words of wisdom...",
        },
        {
            "id": 13,
            "sa": "देहिनोऽस्मिन्यथा देहे कौमारं यौवनं जरा |",
            "tr": "dehino ’smin yathā dehe kaumāraṁ yauvanaṁ jarā |",
            "en": "Just as the embodied soul passes in this body, from boyhood to youth to old age...",
        },
    ],
    3: [
        {
            "id": 8,
            "sa": "नियतं कुरु कर्म त्वं कर्म ज्यायो ह्यकर्मणः |",
            "tr": "niyataṁ kuru karma tvaṁ karma jyāyo hy akarmaṇaḥ |",
            "en": "Perform your prescribed duty, for doing so is better than not working...",
        }
    ],
}

@app.get("/test")
async def test_db():
    col = await get_collection("health")
    doc = {"ok": True}
    await col.insert_one(doc)
    count = await col.count_documents({})
    return {"database": "ok", "count": int(count)}

@app.get("/api/chapters")
async def get_chapters():
    return {"chapters": CHAPTERS}

@app.get("/api/verses")
async def get_verses(chapter_id: int = Query(...), verse_id: int | None = None):
    verses = VERSES.get(chapter_id, [])
    if verse_id is not None:
        verses = [v for v in verses if v["id"] == verse_id]
    return {"verses": verses}

@app.get("/api/search")
async def search(q: str = ""):
    ql = q.lower()
    results = []
    for cid, lst in VERSES.items():
        for v in lst:
            if ql in v["tr"].lower() or ql in v["en"].lower() or ql in v["sa"]:
                results.append({"chapter_id": cid, **v})
    return {"results": results}

@app.get("/api/daily_verse")
async def daily_verse():
    # deterministic pick: use sum of lengths modulo
    allv = [(cid, v) for cid, lst in VERSES.items() for v in lst]
    if not allv:
        return JSONResponse({"message": "no verses"}, status_code=404)
    idx = (sum(len(v[1]["tr"]) for v in allv)) % len(allv)
    cid, v = allv[idx]
    return {"chapter_id": cid, **v}

@app.post("/api/evaluate_pronunciation", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    a = req.target
    b = req.spoken
    sm = SequenceMatcher(None, a, b)
    score = round(sm.ratio() * 100, 2)
    diffs: list[DiffItem] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        diffs.append(DiffItem(op=tag, a=a[i1:i2], b=b[j1:j2]))
    return EvaluateResponse(score=score, diffs=diffs)

@app.post("/api/bookmarks")
async def add_bookmark(b: Bookmark):
    doc = await create_document("bookmark", b.model_dump())
    doc["_id"] = str(doc.get("_id"))
    return doc

@app.get("/api/bookmarks")
async def list_bookmarks(user_id: str):
    docs = await get_documents("bookmark", {"user_id": user_id}, limit=500)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}

@app.post("/api/progress")
async def add_progress(p: Progress):
    doc = await create_document("progress", p.model_dump())
    doc["_id"] = str(doc.get("_id"))
    return doc

@app.get("/api/progress")
async def list_progress(user_id: str):
    docs = await get_documents("progress", {"user_id": user_id}, limit=1000)
    for d in docs:
        d["_id"] = str(d.get("_id"))
    return {"items": docs}

@app.get("/api/stats")
async def stats(user_id: str):
    bms = await get_documents("bookmark", {"user_id": user_id}, limit=1000)
    prs = await get_documents("progress", {"user_id": user_id}, limit=1000)
    practiced = len(prs)
    mastered = sum(1 for p in prs if float(p.get("score", 0)) >= 85)
    avg_score = round(sum(float(p.get("score", 0)) for p in prs) / practiced, 2) if practiced else 0
    return {"bookmarks": len(bms), "practiced": practiced, "mastered": mastered, "avg_score": avg_score}

@app.post("/api/practice/export")
async def export_csv(payload: ExportRequest):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["chapter_id", "verse_id", "sa", "tr", "en"])
    for item in payload.items:
        cid = item.chapter_id
        vid = item.verse_id
        verse = next((v for v in VERSES.get(cid, []) if v["id"] == vid), None)
        if verse:
            writer.writerow([cid, vid, verse["sa"], verse["tr"], verse["en"]])
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=practice.csv"})

@app.post("/api/chatbot")
async def chatbot(req: ChatRequest):
    last = next((m for m in reversed(req.messages) if m.role == "user"), None)
    text = last.content if last else ""
    t = text.lower()
    if any(k in t for k in ["calm", "fear", "anxiety"]):
        return {"reply": "Be steadfast in yoga; perform your duty without attachment to success or failure. (BG 2.48)"}
    if any(k in t for k in ["karma", "action", "duty"]):
        return {"reply": "Perform prescribed duty; action is superior to inaction. (BG 3.8)"}
    return {"reply": "Reflect on the impermanence of the body and steadiness of the soul. (BG 2.13)"}
