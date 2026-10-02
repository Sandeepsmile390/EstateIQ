"""
EstateIQ Facility Intelligence - MongoDB Database Connector & Integration Module
Provides robust MongoDB connectivity, connection pooling, and seamless fallback
for operational telemetry, ML prediction logs, decision traces, and user sessions.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("EstateIQ.MongoDB")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "estateiq_db")

_mongo_client = None
_mongo_db = None
_is_connected = False

# In-memory fallback document store if MongoDB service is unreachable
_fallback_store: Dict[str, List[Dict[str, Any]]] = {
    "telemetry": [],
    "predictions": [],
    "decision_traces": [],
    "users": [],
    "scenarios": [],
    "actionable_rules": []
}


def connect_mongo_db() -> bool:
    """
    Establishes connection to MongoDB instance using PyMongo.
    Returns True if connection succeeds, False if falling back to in-memory store.
    """
    global _mongo_client, _mongo_db, _is_connected
    try:
        import pymongo
        _mongo_client = pymongo.MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000
        )
        # Test server availability
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client[MONGODB_DB_NAME]
        _is_connected = True
        logger.info(f"Successfully connected to MongoDB at {MONGODB_URI} (DB: {MONGODB_DB_NAME})")
        return True
    except Exception as e:
        _is_connected = False
        _mongo_client = None
        _mongo_db = None
        logger.warning(f"MongoDB connection failed ({str(e)}). Active mode: In-Memory DB Fallback.")
        return False


def get_mongo_db():
    """Returns PyMongo database instance if connected, else None."""
    global _mongo_db, _is_connected
    if not _is_connected or _mongo_db is None:
        connect_mongo_db()
    return _mongo_db


def close_mongo_db():
    """Closes active MongoDB client connection."""
    global _mongo_client, _is_connected
    if _mongo_client:
        try:
            _mongo_client.close()
        except Exception:
            pass
    _is_connected = False
    _mongo_client = None


def get_db_status() -> Dict[str, Any]:
    """Returns MongoDB connectivity status, mode, and collection counts."""
    db = get_mongo_db()
    if _is_connected and db is not None:
        try:
            collections = db.list_collection_names()
            stats = {}
            for col in ["telemetry", "predictions", "decision_traces", "users", "scenarios", "actionable_rules"]:
                stats[col] = db[col].count_documents({})
            return {
                "status": "connected",
                "engine": "MongoDB",
                "uri": MONGODB_URI,
                "database": MONGODB_DB_NAME,
                "collections": stats
            }
        except Exception as e:
            logger.warning(f"Error reading MongoDB collection stats: {e}")

    # Fallback response
    return {
        "status": "fallback_in_memory",
        "engine": "In-Memory Document Store (MongoDB Interface Compatible)",
        "uri": MONGODB_URI,
        "database": MONGODB_DB_NAME,
        "collections": {k: len(v) for k, v in _fallback_store.items()}
    }


def save_prediction_log(collection_name: str, payload: Dict[str, Any]) -> str:
    """Saves ML prediction record into specified collection."""
    db = get_mongo_db()
    doc = dict(payload)
    if "timestamp" not in doc:
        doc["timestamp"] = datetime.now(timezone.utc).isoformat()

    if _is_connected and db is not None:
        try:
            res = db[collection_name].insert_one(doc)
            return str(res.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert document into MongoDB {collection_name}: {e}")

    # In-memory fallback
    doc["_id"] = f"mem_doc_{len(_fallback_store.get(collection_name, [])) + 1}"
    _fallback_store.setdefault(collection_name, []).append(doc)
    return doc["_id"]


def query_prediction_logs(collection_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches recent prediction logs from collection."""
    db = get_mongo_db()
    if _is_connected and db is not None:
        try:
            cursor = db[collection_name].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to query MongoDB collection {collection_name}: {e}")

    # In-memory fallback
    items = _fallback_store.get(collection_name, [])
    # Return reverse sorted
    return [dict(x) for x in reversed(items[-limit:])]
