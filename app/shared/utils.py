# app/shared/utils.py - Utility Functions

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

async def get_current_user_from_session(request: Request) -> Dict[str, Any]:
    """
    Get current user from session - Matches your existing auth system
    """
    
    try:
        # Get user session from cookie (matches your auth system)
        user_session = request.cookies.get("user_session")
        
        if not user_session:
            logger.info("🔒 No session cookie found, returning demo user")
            # Return demo user when no session
            return {
                "_id": "demo_user_123",
                "fullName": "Demo EcoWarrior",
                "email": "demo@meriDharani.com",
                "role": "citizen",
                "language": "en",
                "phone": "+91-9876543210",
                "location": {
                    "city": "Yanamalakuduru",
                    "state": "Andhra Pradesh", 
                    "pincode": "521456"
                },
                "citizenProfile": {
                    "languagePreference": "en",
                    "notificationPreferences": ["push", "sms"],
                    "totalReports": 0,
                    "totalPoints": 0,
                    "level": "eco_rookie"
                },
                "isActive": True,
                "isVerified": True,
                "reputation": 5.0
            }
        
        # If session exists, try to get user from database
        try:
            from ..shared.database import database
            
            if database.database is None:
                logger.warning("⚠️ Database not connected, using demo mode")
                # Demo mode - decode session to get user data
                if user_session == "demo_citizen_123":
                    return {
                        "_id": "demo_citizen_123",
                        "fullName": "Demo Citizen",
                        "email": "demo@meriDharani.com",
                        "role": "citizen", 
                        "language": "en",
                        "phone": "+91-9876543210",
                        "location": {
                            "city": "Yanamalakuduru",
                            "state": "Andhra Pradesh",
                            "pincode": "521456"
                        },
                        "citizenProfile": {
                            "languagePreference": "en",
                            "notificationPreferences": ["push", "sms"],
                            "totalReports": 5,
                            "totalPoints": 75,
                            "level": "waste_warrior"
                        },
                        "isActive": True,
                        "isVerified": True,
                        "reputation": 4.5
                    }
            else:
                # Real database lookup
                from bson import ObjectId
                
                # Try to find user by session ID
                user = await database.database.users.find_one({"_id": ObjectId(user_session)})
                
                if user:
                    # Convert ObjectId to string and extract language preference
                    user["_id"] = str(user["_id"])
                    
                    # Get language from citizenProfile or default to 'en'
                    language = "en"
                    if user.get("citizenProfile"):
                        language = user["citizenProfile"].get("languagePreference", "en")
                    elif user.get("workerProfile"):
                        language = user["workerProfile"].get("languagePreference", "en")
                    elif user.get("governmentProfile"):
                        language = user["governmentProfile"].get("languagePreference", "en")
                    
                    user["language"] = language
                    
                    logger.info(f"👤 Found user: {user.get('fullName')} ({user['_id']})")
                    return user
                else:
                    logger.warning(f"⚠️ User not found for session: {user_session}")
        
        except Exception as db_error:
            logger.error(f"❌ Database lookup failed: {db_error}")
        
        # Fallback to demo user if anything fails
        logger.info("🔄 Falling back to demo user")
        return {
            "_id": "demo_fallback_123",
            "fullName": "Demo User",
            "email": "demo@example.com",
            "role": "citizen",
            "language": "en",
            "phone": "+91-9876543210",
            "location": {
                "city": "Yanamalakuduru",
                "state": "Andhra Pradesh",
                "pincode": "521456"
            },
            "citizenProfile": {
                "languagePreference": "en",
                "notificationPreferences": ["push", "sms"],
                "totalReports": 0,
                "totalPoints": 0,
                "level": "eco_rookie"
            },
            "isActive": True,
            "isVerified": False,
            "reputation": 5.0
        }
        
    except Exception as e:
        logger.error(f"❌ Session error: {e}")
        # Return fallback user on error
        return {
            "_id": "fallback_user",
            "fullName": "Anonymous User",
            "email": "anonymous@example.com",
            "role": "citizen",
            "language": "en",
            "phone": None,
            "location": {
                "city": "Unknown",
                "state": "Unknown",
                "pincode": "000000"
            },
            "citizenProfile": {
                "languagePreference": "en",
                "notificationPreferences": ["push"],
                "totalReports": 0,
                "totalPoints": 0,
                "level": "eco_rookie"
            },
            "isActive": False,
            "isVerified": False,
            "reputation": 0.0
        }

def get_user_language(user_data: Dict[str, Any]) -> str:
    """Extract user's preferred language from user data"""
    try:
        # Check citizenProfile first
        if user_data.get("citizenProfile"):
            return user_data["citizenProfile"].get("languagePreference", "en")
        
        # Check workerProfile
        if user_data.get("workerProfile"):
            return user_data["workerProfile"].get("languagePreference", "en")
        
        # Check governmentProfile
        if user_data.get("governmentProfile"):
            return user_data["governmentProfile"].get("languagePreference", "en")
        
        # Check direct language field
        if user_data.get("language"):
            return user_data["language"]
        
        # Default to English
        return "en"
        
    except Exception as e:
        logger.error(f"❌ Language extraction error: {e}")
        return "en"

def generate_secure_id(prefix: str = "", length: int = 8) -> str:
    """Generate secure random ID"""
    import uuid
    random_part = str(uuid.uuid4())[:length].upper()
    timestamp = int(datetime.utcnow().timestamp())
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    else:
        return f"{timestamp}_{random_part}"

def hash_data(data: str) -> str:
    """Create hash of data for security/caching"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def validate_file_type(filename: str, allowed_extensions: list = None) -> bool:
    """Validate uploaded file type"""
    if allowed_extensions is None:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
    
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = f"{name[:90]}.{ext}" if ext else name[:100]
    
    return filename

def create_response(success: bool, message: str, data: Any = None, error: str = None) -> Dict[str, Any]:
    """Create standardized API response"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    
    if error is not None:
        response["error"] = error
    
    return response

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    import math
    
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude coordinates"""
    try:
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)
    except (TypeError, ValueError):
        return False

def get_indian_time() -> datetime:
    """Get current time in Indian timezone"""
    from datetime import timezone, timedelta
    
    # India timezone (UTC+5:30)
    india_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(india_tz)

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data like phone numbers, emails"""
    if not data or len(data) <= visible_chars:
        return data
    
    if '@' in data:  # Email
        local, domain = data.split('@', 1)
        if len(local) <= visible_chars:
            return f"{local}@{domain}"
        return f"{local[:2]}***{local[-2:]}@{domain}"
    else:  # Phone or other
        return f"{data[:visible_chars]}***{data[-visible_chars:]}"

def validate_indian_phone(phone: str) -> bool:
    """Validate Indian phone number format"""
    import re
    # Pattern for +91-XXXXXXXXXX format
    pattern = r'^\+91-[6789]\d{9}$'
    return bool(re.match(pattern, phone))

def clean_text_input(text: str, max_length: int = 1000) -> str:
    """Clean and validate text input"""
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    text = ' '.join(text.split())
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].strip()
    
    return text

def is_production() -> bool:
    """Check if running in production environment"""
    import os
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

def log_user_action(user_id: str, action: str, details: Dict = None):
    """Log user action for audit trail"""
    try:
        log_data = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        # In production, this could write to audit log
        if is_production():
            # TODO: Write to audit collection or log file
            pass
        else:
            logger.info(f"🔍 User Action: {json.dumps(log_data)}")
            
    except Exception as e:
        logger.error(f"❌ Failed to log user action: {e}")

def is_database_connected(database_instance):
    """
    🔧 FIXED: Proper database connection check
    Replaces problematic: if database: 
    """
    try:
        return (
            database_instance is not None and
            hasattr(database_instance, 'database') and 
            database_instance.database is not None and 
            hasattr(database_instance, 'is_connected') and 
            database_instance.is_connected
        )
    except Exception as e:
        print(f"❌ Database check error: {e}")
        return False

async def safe_database_operation(database_instance, operation_func, *args, **kwargs):
    """
    🔧 SAFE: Execute database operation with proper error handling
    Usage: await safe_database_operation(database, lambda db: db.collection.find_one(query))
    """
    try:
        if not is_database_connected(database_instance):
            print("⚠️ Database not connected - skipping operation")
            return None
            
        return await operation_func(database_instance.database, *args, **kwargs)
        
    except Exception as e:
        print(f"❌ Database operation error: {e}")
        return None
