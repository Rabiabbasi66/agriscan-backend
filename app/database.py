from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, GEOSPHERE
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = None
        self.database = None

    async def connect(self):
        if self.client is None:
            # ✅ DIRECT MONGODB URI (Hardcoded)
            MONGODB_URI = "mongodb+srv://fazailabbasi005_db_user:Scout2816@agriscan3d.l8gxxmx.mongodb.net/?appName=Agriscan3d"
            MONGODB_DB_NAME = "agriscan_db"
            
            self.client = AsyncIOMotorClient(
                MONGODB_URI,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
            )
            self.database = self.client[MONGODB_DB_NAME]

            await self.client.admin.command("ping")
            logger.info("✅ MongoDB Connected")
            await self.ensure_indexes()

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
            self.database = None

    async def ensure_indexes(self):
        db = self.database

        await db.users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("phone", ASCENDING)], unique=True, sparse=True),
            IndexModel([("role", ASCENDING)]),
        ])

        await db.farms.create_indexes([
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("location", GEOSPHERE)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        await db.fields.create_indexes([
            IndexModel([("farm_id", ASCENDING)]),
            IndexModel([("boundary", GEOSPHERE)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        await db.uploads.create_indexes([
            IndexModel([("field_id", ASCENDING)]),
            IndexModel([("uploaded_by", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        await db.analysis_results.create_indexes([
            IndexModel([("upload_id", ASCENDING)], unique=True),
            IndexModel([("field_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("health_score", DESCENDING)]),
        ])

        await db.jobs.create_indexes([
            IndexModel([("upload_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        # ✅ PREDICTIONS COLLECTION INDEXES
        await db.predictions.create_indexes([
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("crop", ASCENDING)]),
            IndexModel([("disease", ASCENDING)]),
            IndexModel([("is_healthy", ASCENDING)]),
        ])

        logger.info("✅ MongoDB indexes ensured")

    @property
    def users(self):
        return self.database.users

    @property
    def farms(self):
        return self.database.farms

    @property
    def fields(self):
        return self.database.fields

    @property
    def uploads(self):
        return self.database.uploads

    @property
    def analysis_results(self):
        return self.database.analysis_results

    @property
    def jobs(self):
        return self.database.jobs

    @property
    def predictions(self):
        return self.database.predictions


db = Database()


def get_client():
    return db.client


def get_database():
    if db.database is None:
        raise RuntimeError(
            "Database is not connected. Call await db.connect() first."
        )
    return db.database


async def connect_db():
    await db.connect()


async def close_db():
    await db.close()