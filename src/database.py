from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from urllib.parse import quote_plus

MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", 27017))
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "curriculos_db")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "logs")
MONGODB_USER = os.getenv("MONGODB_USER", "")
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")

if MONGODB_USER and MONGODB_PASSWORD:
    username = quote_plus(MONGODB_USER)
    password = quote_plus(MONGODB_PASSWORD)
    connection_string = f"mongodb://{username}:{password}@{MONGODB_HOST}:{MONGODB_PORT}"
else:
    connection_string = f"mongodb://{MONGODB_HOST}:{MONGODB_PORT}"

client = AsyncIOMotorClient(connection_string)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]


async def log_request(
    request_id: str,
    user_id: str,
    query: str,
    resultado: str,
    files_count: int,
    status: str = "success"
):
    timestamp_sp = datetime.utcnow() - timedelta(hours=3)

    log_entry = {
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": timestamp_sp,
        "query": query,
        "resultado": resultado[:500],
        "files_count": files_count,
        "status": status
    }

    await collection.insert_one(log_entry)
