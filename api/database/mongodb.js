import dotenv from "dotenv";
import { MongoClient } from "mongodb";

dotenv.config();

const mongoEnv = process.env.MONGO_ENV || "local";
const uri =
  mongoEnv === "atlas"
    ? process.env.MONGODB_URI_ATLAS
    : process.env.MONGODB_URI_LOCAL;

if (!uri) {
  throw new Error("❌ No MongoDB URI configured in .env");
}

const client = new MongoClient(uri);

await client.connect();
console.log(`✅ Connected to MongoDB (${mongoEnv})`);

// Expose db object ready to use
const db = client.db("mydb");

export { db };
