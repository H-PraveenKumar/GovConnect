"""
MongoDB service for database operations
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
import logging

from ..config import settings
from ..models.scheme import Scheme, SchemeRule
from ..models.user import UserProfile, EligibilityResult

logger = logging.getLogger(__name__)


class MongoService:
    """Service for MongoDB operations"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.fs: Optional[AsyncIOMotorGridFSBucket] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_db_name]
            self.fs = AsyncIOMotorGridFSBucket(self.db)
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    async def health_check(self) -> bool:
        """Check MongoDB connection health"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    # GridFS operations for PDF storage
    async def store_pdf(self, filename: str, content: bytes, metadata: Dict[str, Any]) -> ObjectId:
        """Store PDF file in GridFS"""
        try:
            file_id = await self.fs.upload_from_stream(
                filename,
                content,
                metadata=metadata
            )
            logger.info(f"PDF stored successfully with ID: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to store PDF: {e}")
            raise
    
    async def get_pdf(self, file_id: ObjectId) -> bytes:
        """Retrieve PDF file from GridFS"""
        try:
            grid_out = await self.fs.open_download_stream(file_id)
            content = await grid_out.read()
            await grid_out.close()
            return content
        except Exception as e:
            logger.error(f"Failed to retrieve PDF: {e}")
            raise
    
    async def delete_pdf(self, file_id: ObjectId) -> bool:
        """Delete PDF file from GridFS"""
        try:
            await self.fs.delete(file_id)
            logger.info(f"PDF deleted successfully: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete PDF: {e}")
            return False
    
    # Scheme operations
    async def create_scheme(self, scheme: Scheme) -> Scheme:
        """Create a new scheme"""
        try:
            scheme_dict = scheme.model_dump(by_alias=True)
            result = await self.db.schemes.insert_one(scheme_dict)
            scheme.id = result.inserted_id
            logger.info(f"Scheme created: {scheme.scheme_id}")
            return scheme
        except Exception as e:
            logger.error(f"Failed to create scheme: {e}")
            raise
    
    async def get_scheme(self, scheme_id: str) -> Optional[Scheme]:
        """Get scheme by ID"""
        try:
            doc = await self.db.schemes.find_one({"scheme_id": scheme_id})
            if doc:
                return Scheme(**doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get scheme: {e}")
            raise
    
    async def update_scheme_status(self, scheme_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """Update scheme processing status"""
        try:
            update_data = {"status": status, "updated_at": datetime.now(datetime.timezone.utc)}
            if error_message:
                update_data["error_message"] = error_message
            
            result = await self.db.schemes.update_one(
                {"scheme_id": scheme_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update scheme status: {e}")
            return False
    
    async def get_all_schemes(self, status: Optional[str] = None) -> List[Scheme]:
        """Get all schemes, optionally filtered by status"""
        try:
            filter_query = {}
            if status:
                filter_query["status"] = status
            
            cursor = self.db.schemes.find(filter_query)
            schemes = []
            async for doc in cursor:
                schemes.append(Scheme(**doc))
            return schemes
        except Exception as e:
            logger.error(f"Failed to get schemes: {e}")
            raise
    
    # Scheme rules operations
    async def create_scheme_rule(self, rule: SchemeRule) -> SchemeRule:
        """Create scheme rules"""
        try:
            rule_dict = rule.model_dump()
            result = await self.db.scheme_rules.insert_one(rule_dict)
            rule.id = result.inserted_id
            logger.info(f"Scheme rules created: {rule.scheme_id}")
            return rule
        except Exception as e:
            logger.error(f"Failed to create scheme rules: {e}")
            raise
    
    async def get_scheme_rule(self, scheme_id: str) -> Optional[SchemeRule]:
        """Get scheme rules by scheme ID"""
        try:
            doc = await self.db.scheme_rules.find_one({"scheme_id": scheme_id})
            if doc:
                return SchemeRule(**doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get scheme rules: {e}")
            raise
    
    async def get_all_scheme_rules(self) -> List[SchemeRule]:
        """Get all scheme rules"""
        try:
            cursor = self.db.scheme_rules.find()
            rules = []
            async for doc in cursor:
                rules.append(SchemeRule(**doc))
            return rules
        except Exception as e:
            logger.error(f"Failed to get scheme rules: {e}")
            raise
    
    # User operations
    async def create_user(self, user_id: str, profile: UserProfile) -> bool:
        """Create or update user profile"""
        try:
            user_data = {
                "user_id": user_id,
                "profile": profile.model_dump(),
                "created_at": datetime.now(datetime.timezone.utc),
                "updated_at": datetime.now(datetime.timezone.utc)
            }
            
            result = await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": user_data},
                upsert=True
            )
            logger.info(f"User profile created/updated: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        try:
            doc = await self.db.users.find_one({"user_id": user_id})
            return doc
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    # Eligibility results operations
    async def store_eligibility_result(self, user_id: str, result: EligibilityResult) -> bool:
        """Store eligibility check result"""
        try:
            result_data = {
                "user_id": user_id,
                "scheme_id": result.scheme_id,
                "is_eligible": result.is_eligible,
                "reasons": result.reasons,
                "required_documents": result.required_documents,
                "checked_at": datetime.now(datetime.timezone.utc)
            }
            
            await self.db.eligibility_results.update_one(
                {"user_id": user_id, "scheme_id": result.scheme_id},
                {"$set": result_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store eligibility result: {e}")
            return False
    
    async def get_user_eligibility_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's eligibility check history"""
        try:
            cursor = self.db.eligibility_results.find({"user_id": user_id})
            results = []
            async for doc in cursor:
                results.append(doc)
            return results
        except Exception as e:
            logger.error(f"Failed to get eligibility history: {e}")
            return []
    
    # Statistics and analytics
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = {
                "total_schemes": await self.db.schemes.count_documents({}),
                "completed_schemes": await self.db.schemes.count_documents({"status": "completed"}),
                "processing_schemes": await self.db.schemes.count_documents({"status": "processing"}),
                "failed_schemes": await self.db.schemes.count_documents({"status": "failed"}),
                "total_scheme_rules": await self.db.scheme_rules.count_documents({}),
                "total_users": await self.db.users.count_documents({}),
                "total_eligibility_checks": await self.db.eligibility_results.count_documents({})
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global MongoDB service instance
mongo_service = MongoService()
