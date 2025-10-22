# app/shared/session_manager.py - UNIFIED SESSION MANAGEMENT

import logging
from fastapi import Request, HTTPException
from typing import Dict, Any, Optional
from bson import ObjectId
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionManager:
    """Unified session management for all routes"""
    
    def __init__(self):
        self.demo_users = {
            "citizen": {
                "_id": "demo_citizen_001",
                "fullName": "Demo EcoWarrior",
                "email": "demo@meridharani.com",
                "role": "citizen",
                "phone": "+91-9876543210",
                "location": {
                    "city": "Vijayawada",
                    "state": "Andhra Pradesh",
                    "pincode": "521456"
                },
                "citizenProfile": {
                    "totalReports": 12,
                    "totalPoints": 850,
                    "level": "eco_champion"
                }
            },
            "worker": {
                "_id": "demo_worker_001",
                "fullName": "Demo CleanGuard",
                "email": "worker@meridharani.com",
                "role": "worker",
                "phone": "+91-9876543211",
                "location": {
                    "city": "Vijayawada",
                    "state": "Andhra Pradesh",
                    "pincode": "521456"
                },
                "workerProfile": {
                    "organizationName": "Independent Worker",
                    "totalJobsCompleted": 145,
                    "averageRating": 4.8,
                    "totalEarnings": 28500
                }
            },
            "government": {
                "_id": "demo_gov_001",
                "fullName": "Demo CityMaster",
                "email": "admin@meridharani.com",
                "role": "government",
                "phone": "+91-9876543212",
                "location": {
                    "city": "Vijayawada",
                    "state": "Andhra Pradesh"
                }
            }
        }
    
    async def get_current_user(self, request: Request, required_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current user from session with proper error handling
        
        Args:
            request: FastAPI request object
            required_role: Optional role requirement ('citizen', 'worker', 'government')
            
        Returns:
            User dictionary with complete profile data
        """
        try:
            # Get session cookie
            user_session = request.cookies.get("user_session")
            
            if not user_session:
                logger.warning("No session cookie found")
                return self._get_demo_user(required_role)
            
            logger.info(f"Found session: {user_session}")
            
            # Handle demo sessions
            if user_session.startswith('demo'):
                return self._get_demo_user_by_session(user_session, required_role)
            
            # Try to get real user from database
            real_user = await self._get_user_from_database(user_session)
            
            if real_user:
                # Validate role if required
                if required_role and real_user.get('role') != required_role:
                    logger.warning(f"Role mismatch: expected {required_role}, got {real_user.get('role')}")
                    return self._get_demo_user(required_role)
                
                logger.info(f"Real user loaded: {real_user.get('fullName')}")
                return real_user
            else:
                logger.warning(f"No user found for session: {user_session}")
                return self._get_demo_user(required_role)
                
        except Exception as e:
            logger.error(f"Session error: {e}")
            return self._get_demo_user(required_role)
    
    async def _get_user_from_database(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database with proper error handling"""
        try:
            from .database import database
            
            # Check database availability
            if not hasattr(database, 'database') or database.database is None:
                logger.warning("Database not available")
                return None
            
            # Try ObjectId conversion first
            try:
                query = {"_id": ObjectId(user_id)}
            except:
                # If ObjectId fails, try string ID
                query = {"_id": user_id}
            
            user = await database.database.users.find_one(query)
            
            if user:
                # Convert ObjectId to string for JSON serialization
                user["_id"] = str(user["_id"])
                
                # Update last seen
                await database.database.users.update_one(
                    {"_id": ObjectId(user["_id"]) if not isinstance(user["_id"], str) else user["_id"]},
                    {"$set": {"lastSeen": datetime.utcnow()}}
                )
                
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return None
    
    def _get_demo_user(self, role: Optional[str] = None) -> Dict[str, Any]:
        """Get demo user based on role"""
        if role and role in self.demo_users:
            return self.demo_users[role].copy()
        
        # Default to citizen demo user
        return self.demo_users["citizen"].copy()
    
    def _get_demo_user_by_session(self, session: str, required_role: Optional[str] = None) -> Dict[str, Any]:
        """Get demo user based on session string"""
        if "citizen" in session:
            return self.demo_users["citizen"].copy()
        elif "worker" in session:
            return self.demo_users["worker"].copy()
        elif "government" in session or "gov" in session:
            return self.demo_users["government"].copy()
        
        # Fallback to required role or citizen
        return self._get_demo_user(required_role)
    
    def create_session_cookie(self, user_id: str, remember_me: bool = False) -> Dict[str, Any]:
        """Create session cookie configuration"""
        max_age = 24 * 3600 if remember_me else 3600  # 24 hours or 1 hour
        
        return {
            "key": "user_session",
            "value": user_id,
            "max_age": max_age,
            "httponly": True,
            "secure": False,  # Set to True in production with HTTPS
            "samesite": "lax"
        }
    
    def clear_session_cookie(self) -> Dict[str, Any]:
        """Clear session cookie configuration"""
        return {
            "key": "user_session",
            "httponly": True,
            "secure": False,
            "samesite": "lax"
        }

# Global session manager instance
session_manager = SessionManager()

# Convenience function for routes
async def get_current_user_from_session(request: Request, required_role: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for getting current user from session
    
    Usage in routes:
        user = await get_current_user_from_session(request, "worker")
    """
    return await session_manager.get_current_user(request, required_role)