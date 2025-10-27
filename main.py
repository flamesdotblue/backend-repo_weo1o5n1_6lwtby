import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict
from io import StringIO
from datetime import datetime
from difflib import SequenceMatcher

from database import db, create_document, get_documents
from schemas import Progress, Bookmark, PracticeItem, ChatMessage, EvaluateRequest, EvaluateResponse, ExportRequest

app = FastAPI(title="Gita Pronunciation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Minimal verse dataset for demo (extendable). In production, store in DB.
VERSES: Dict[int, List[Dict]] = {
    1: [
        {
            "id": "1.1",
            "devanagari": "धृतराष्ट्र उवाच | धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः | मामकाः पाण्डवाश्चैव किमकुर्वत संजय ||",
            "transliteration": "dhṛtarāṣṭra uvāca | dharma-kṣetre kuru-kṣetre samavetā yuyutsavaḥ | māmakāḥ pāṇḍavāś caiva kim akurvata sañjaya ||",
            "translations": {
                "en": "Dhritarashtra said: O Sanjaya, after assembling on the holy field of Kurukshetra and desiring to fight, what did my sons and the sons of Pandu do?",
                "hi": "धृतराष्ट्र बोले: हे संजय! धर्मभूमि कुरुक्षेत्र में युद्ध की इच्छा से एकत्रित हुए मेरे पुत्रों और पाण्डु के पुत्रों ने क्या किया?"
            }
        }
    ],
    2: [
        {
            "id": "2.47",
            "devanagari": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन | मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ||",
            "transliteration": "karmaṇy-evādhikāras te mā phaleṣu kadācana | mā karma-phala-hetur bhūr mā te saṅgo 'stvakarmaṇi ||",
            "translations": {
                "en": "You have a right to perform your prescribed duty, but you are not entitled to the fruits of action.",
                "hi": "तुम्हारा अधिकार केवल कर्म करने में है, उसके फलों में कभी नहीं।"
            }
        },
        {
            "id": "2.50",
            "devanagari": "योगः कर्मसु कौशलम् |",
            "transliteration": "yogaḥ karmasu kauśalam |",
            "translations": {
                "en": "Yoga is skill in action.",
                "hi": "योग कर्मों में कौशल है।"
            }
        }
    ],
    12: [
        {
            "id": "12.15",
            "devanagari": "यस्मान्नोद्विजते लोको लोकान्नोद्विजते च यः | हर्षामर्षभयोद्वेगैर्मुक्तो यः स च मे प्रियः ||",
            "transliteration": "yasmān nodvijate loko lokān nodvijate ca yaḥ | harṣāmarṣa-bhayodvegair mukto yaḥ sa ca me priyaḥ ||",
            "translations": {
                "en": "He by whom the world is not agitated and who is not agitated by the world... he is dear to Me.",
                "hi": "जिससे लोक विचलित नहीं होते और जो लोक से विचलित नहीं होता... वह मुझे प्रिय है।"
            }
        }
    ]
}

CHAPTERS = [{"number": i, "name": f"Chapter {i}"} for i in range(1, 19)]

@app.get("/")
def read_root():
    return {"message": "Gita Pronunciation API running"}

@app.get("/api/chapters")
def get_chapters():
    return {"chapters": CHAPTERS}

@app.get("/api/verses")
def get_verses(chapter: int):
    verses = VERSES.get(chapter, [])
    return {"chapter": chapter, "verses": verses}

@app.get("/api/search")
def search(q: str):
    ql = q.lower()
    results = []
    for ch, verses in VERSES.items():
        for v in verses:
            text = " ".join([v["devanagari"], v["transliteration"], *v["translations"].values()]).lower()
            if ql in text:
                results.append({"chapter": ch, **v})
    return {"results": results}

@app.get("/api/daily_verse")
def daily_verse():
    all_verses = [(ch, v) for ch, vs in VERSES.items() for v in vs]
    ch, v = random.choice(all_verses)
    return {"chapter": ch, **v}

# Pronunciation evaluation using simple sequence matching
@app.post("/api/evaluate_pronunciation", response_model=EvaluateResponse)
def evaluate_pronunciation(payload: EvaluateRequest):
    target = payload.target_text.strip().lower()
    spoken = payload.recognized_text.strip().lower()

    matcher = SequenceMatcher(a=target, b=spoken)
    opcodes = matcher.get_opcodes()
    diffs = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag != 'equal' and i1 != i2:
            diffs.append({"start": i1, "end": i2})
    score = matcher.ratio() * 100.0
    return EvaluateResponse(score=round(score, 2), differences=diffs)

# Bookmarks
@app.post("/api/bookmarks")
def add_bookmark(b: Bookmark):
    bid = create_document("bookmark", b)
    return {"id": bid}

@app.get("/api/bookmarks")
def list_bookmarks(user_id: str = "public"):
    docs = get_documents("bookmark", {"user_id": user_id})
    for d in docs:
        d["_id"] = str(d["_id"])  # jsonify
    return {"items": docs}

# Progress
@app.post("/api/progress")
def upsert_progress(p: Progress):
    # Simple insert-only for demo; could be upsert with unique key
    pid = create_document("progress", p)
    return {"id": pid}

@app.get("/api/progress")
def get_progress(user_id: str = "public"):
    docs = get_documents("progress", {"user_id": user_id})
    for d in docs:
        d["_id"] = str(d["_id"])  # jsonify
    return {"items": docs}

# Stats
@app.get("/api/stats")
def stats(user_id: str = "public"):
    bookmarks = get_documents("bookmark", {"user_id": user_id})
    progress = get_documents("progress", {"user_id": user_id})
    mastered = [p for p in progress if p.get("status") == "mastered"]
    avg_score = round(sum(p.get("score", 0) for p in progress) / len(progress), 2) if progress else 0.0
    return {
        "bookmark_count": len(bookmarks),
        "progress_count": len(progress),
        "mastered_count": len(mastered),
        "avg_score": avg_score,
    }

# Practice list export (CSV)
@app.post("/api/practice/export")
def export_practice(req: ExportRequest):
    items = get_documents("practiceitem", {"user_id": req.user_id})
    output = StringIO()
    output.write("chapter,verse_id,phrase\n")
    for it in items:
        output.write(f"{it.get('chapter')},{it.get('verse_id')},\"{(it.get('phrase') or '').replace('\\', ' ').replace('"', "''")}\"\n")
    output.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=practice_{req.user_id}.csv"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)

# Chatbot (rule-based mini helper)
@app.post("/api/chatbot")
def chatbot(msg: ChatMessage):
    user_text = msg.message.lower()
    suggestions = []
    # Very small keyword mapping
    if any(k in user_text for k in ["anxiety", "worry", "fear", "भय", "चिंता"]):
        suggestions.append({"chapter": 12, **VERSES[12][0]})
    if any(k in user_text for k in ["duty", "काम", "फल", "result", "attachment"]):
        suggestions.append({"chapter": 2, **VERSES[2][0]})
    if not suggestions:
        suggestions.append({"chapter": 2, **VERSES[2][1]})
    response = {
        "reply": "I hear you. Here's a teaching that may help.",
        "verses": suggestions
    }
    return JSONResponse(response)

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
        else:
            response["database"] = "❌ Not configured"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
