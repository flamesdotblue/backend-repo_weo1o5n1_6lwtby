import os
from typing import Any, Dict, Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

_client: Optional[AsyncIOMotorClient] = None
_db = None

async def get_db():
    global _client, _db
    if _client is None:
        _client = AsyncIOMotorClient(DATABASE_URL)
        _db = _client[DATABASE_NAME]
    return _db

async def get_collection(name: str) -> AsyncIOMotorCollection:
    db = await get_db()
    return db[name]

async def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import datetime
    col = await get_collection(collection_name)
    payload = {**data, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    res = await col.insert_one(payload)
    payload["_id"] = res.inserted_id
    return payload

async def get_documents(collection_name: str, filter_dict: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    col = await get_collection(collection_name)
    cursor = col.find(filter_dict).limit(limit)
    docs = []
    async for d in cursor:
        docs.append(d)
    return docs
