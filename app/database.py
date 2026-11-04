from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, GEOSPHERE
from pymongo.errors import PyMongoError
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB connection holder.

    Connection settings (URI + database name) come exclusively from the
    application configuration system (app.config.Settings, backed by
    environment variables / a local .env file). No credentials live in code.
    """

    def __init__(self):
        self.client = None
        self.database = None

    async def connect(self) -> bool:
        """Connect to MongoDB. Returns False (instead of crashing the API) when
        the deployment is unreachable: AI inference and the static frontend
        must keep working even if the database is down."""
        if self.client is not None:
            return True

        settings = get_settings()

        try:
            client = AsyncIOMotorClient(
                settings.mongodb_uri,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
            )
            database = client[settings.mongodb_db_name]

            # Verify the connection before using it (DNS + auth + reachability).
            await client.admin.command("ping")
        except (PyMongoError, ValueError) as exc:
            logger.error(
                "MongoDB unavailable — starting without persistence: %s", exc
            )
            return False

        self.client = client
        self.database = database
        logger.info("MongoDB connected")

        try:
            await self.ensure_indexes()
        except PyMongoError:
            logger.exception("MongoDB index creation failed (continuing)")

        return True

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

        await db.predictions.create_indexes([
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("crop", ASCENDING)]),
            IndexModel([("disease", ASCENDING)]),
            IndexModel([("is_healthy", ASCENDING)]),
        ])

        logger.info("MongoDB indexes ensured")

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
