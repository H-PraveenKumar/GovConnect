import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from app.config import settings


class MongoDB:
    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None
    gridfs_bucket: AsyncIOMotorGridFSBucket = None


db = MongoDB()


async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(settings.mongodb_uri)
    db.database = db.client[settings.mongodb_db]
    db.gridfs_bucket = AsyncIOMotorGridFSBucket(db.database, bucket_name="schemes")


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()


def get_database() -> AsyncIOMotorDatabase:
    return db.database


def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    return db.gridfs_bucket
