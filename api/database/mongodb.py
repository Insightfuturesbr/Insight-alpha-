import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_env = os.getenv("MONGO_ENV", "local")

uri = (
    os.getenv("MONGODB_URI_ATLAS")
    if mongo_env == "atlas"
    else os.getenv("MONGODB_URI_LOCAL")
)

if not uri:
    raise RuntimeError("❌ No MongoDB URI configured in .env")

client = MongoClient(uri)
db = client["mydb"]

print(f"✅ Connected to MongoDB ({mongo_env})")
