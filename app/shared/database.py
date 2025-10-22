# app/shared/database.py - Database Connection (Matches your existing system)

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    """MongoDB Database Manager - Matches your existing system"""
    
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.database: AsyncIOMotorDatabase = None
        self.is_connected = False
    
    async def connect_to_database(self):
        """Create database connection"""
        try:
            logger.info("🔌 Connecting to MongoDB...")
            
            # Get MongoDB URL from environment
            mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            database_name = os.getenv("DATABASE_NAME", "meri_dharani")
            
            self.client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=10,
                minPoolSize=1,
                serverSelectionTimeoutMS=5000
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            self.database = self.client[database_name]
            self.is_connected = True
            
            logger.info(f"✅ Connected to MongoDB database: {database_name}")
            
            # Create indexes for better performance
            await self.create_indexes()
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            logger.info("🔄 Continuing in demo mode without database...")
            self.database = None
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            logger.info("🔄 Continuing in demo mode without database...")
            self.database = None
            self.is_connected = False
    
    async def close_database_connection(self):
        """Close database connection"""
        if self.client:
            logger.info("🔌 Closing MongoDB connection...")
            self.client.close()
            self.is_connected = False
            logger.info("✅ MongoDB connection closed")
    
    async def create_indexes(self):
        """Create database indexes for better performance"""
        try:
            if not self.database:
                return
                
            # Users collection indexes
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("phone", unique=True)
            await self.database.users.create_index("role")
            await self.database.users.create_index("isActive")
            await self.database.users.create_index([("location.city", 1), ("location.pincode", 1)])
            
            # User requests collection indexes (for Mithra AI requests)
            await self.database.user_requests.create_index("user_id")
            await self.database.user_requests.create_index("requests.req_id")
            await self.database.user_requests.create_index("requests.status")
            await self.database.user_requests.create_index("requests.created_at")
            await self.database.user_requests.create_index("requests.location.geohash")
            
            # Processing status collection (for real-time updates)
            await self.database.processing_status.create_index([("user_id", 1), ("request_id", 1)], unique=True)
            await self.database.processing_status.create_index("updated_at")
            
            # Worker types collection indexes
            await self.database.worker_types.create_index([("category", 1), ("typeId", 1)], unique=True)
            await self.database.worker_types.create_index("isActive")
            
            # Service areas collection indexes
            await self.database.service_areas.create_index([("city", 1), ("pincode", 1)])
            await self.database.service_areas.create_index("serviceAvailable")
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Index creation warning: {e}")

# Global database instance (matches your existing pattern)
database = Database()

async def get_database() -> Database:
    """
    FastAPI dependency to get database instance
    Matches your existing database pattern
    """
    return database

# Initialize database connection (called during startup)
async def init_database():
    """Initialize database connection"""
    await database.connect_to_database()

# Close database connection (called during shutdown)
async def close_database():
    """Close database connection"""
    await database.close_database_connection()

# Health check function
async def check_database_health() -> dict:
    """Check database connection health"""
    try:
        if database.is_connected and database.database:
            # Try a simple operation
            await database.database.command('ping')
            return {
                "status": "healthy",
                "connected": True,
                "database_name": database.database.name
            }
        else:
            return {
                "status": "disconnected",
                "connected": False,
                "message": "Database not connected - running in demo mode"
            }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }