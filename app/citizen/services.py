# app/citizen/services.py - Enhanced EcoWarrior Business Logic with Profile Updates
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

from ..shared.database import get_database

class CitizenService:
    """Enhanced business logic for EcoWarrior (Citizen) operations"""
    
    def __init__(self):
        self.database = None
    
    async def initialize(self):
        """Initialize database connection - FIXED VERSION"""
        try:
            from ..shared.database import database
            
            # 🔥 FIX: Proper database check
            if (hasattr(database, 'database') and 
                database.database is not None and 
                hasattr(database, 'is_connected') and 
                database.is_connected):
                
                self.database = database.database
                print("✅ CitizenService database initialized")
                return True
            else:
                print("⚠️ Database not available for CitizenService")
                self.database = None
                return False
                
        except Exception as e:
            print(f"❌ CitizenService init error: {e}")
            self.database = None
            return False
    
    # ===================
    # USER MANAGEMENT
    # ===================
    
    async def get_citizen_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get citizen by user ID - FIXED VERSION"""
        print(f"🔍 SERVICE: Looking for user_id: {user_id}")
        try:
            # Initialize if needed
            if not hasattr(self, 'database') or self.database is None:
                await self.initialize()
            
            # 🔥 FIX: Proper database check
            try:
                from ..shared.database import database
                if (hasattr(database, 'database') and 
                    database.database is not None and 
                    hasattr(database, 'is_connected') and 
                    database.is_connected):
                    
                    # Handle demo IDs
                    if user_id.startswith('demo'):
                        return self.create_demo_citizen()
                    
                    # Get from database
                    user = await database.database.users.find_one({
                        "_id": ObjectId(user_id),
                        "role": "citizen"
                    })
                    
                    if user:
                        user["_id"] = str(user["_id"])
                        return self.ensure_citizen_fields(user)
                else:
                    print("⚠️ Database not available, using demo citizen")
                    return self.create_demo_citizen()
                    
            except Exception as db_error:
                print(f"❌ Database lookup error: {db_error}")
                return self.create_demo_citizen()
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting citizen by ID: {e}")
            return None
    
    async def get_citizen_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get citizen by email"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return self.create_demo_citizen()
            
            user = await self.database.users.find_one({
                "email": email.lower().strip(),
                "role": "citizen"
            })
            
            if user:
                user["_id"] = str(user["_id"])
                return self.ensure_citizen_fields(user)
            
            return None
            
        except Exception as e:
            print(f"âŒ Error getting citizen by email: {e}")
            return None
    
    async def get_citizen_from_session(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get citizen data from session info"""
        try:
            user_id = user_info.get('userId')
            
            if user_id:
                # Try to get from database first
                user = await self.get_citizen_by_id(user_id)
                if user:
                    return user
            
            # Fallback to creating from session data
            return self.create_citizen_from_session(user_info)
            
        except Exception as e:
            print(f"âŒ Error getting citizen from session: {e}")
            return self.create_demo_citizen()
    
    def create_citizen_from_session(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create citizen object from session data"""
        user = {
            "_id": user_info.get('userId', 'session_user'),
            "fullName": user_info.get('fullName', 'Unknown User'),
            "email": user_info.get('email', 'unknown@example.com'),
            "phone": "+91-0000000000",
            "role": "citizen",
            "isActive": True,
            "isVerified": user_info.get('isVerified', True),
            "reputation": user_info.get('reputation', 5.0),
            "createdAt": datetime.utcnow()
        }
        
        return self.ensure_citizen_fields(user)
    
    def create_demo_citizen(self) -> Dict[str, Any]:
        """Create demo citizen for testing"""
        user = {
            "_id": "demo_citizen_123",
            "fullName": "Demo EcoWarrior",
            "email": "demo@example.com",
            "phone": "+91-9876543210",
            "role": "citizen",
            "isActive": True,
            "isVerified": True,
            "emailVerified": True,
            "phoneVerified": True,
            "reputation": 4.8,
            "createdAt": datetime.utcnow(),
            "profilePicture": "https://via.placeholder.com/400x400/22c55e/ffffff?text=Demo"
        }
        
        return self.ensure_citizen_fields(user)
    
    def ensure_citizen_fields(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure user has all required fields for citizen"""
        if not user:
            return self.create_demo_citizen()
        
        # Ensure citizenProfile exists
        if "citizenProfile" not in user:
            user["citizenProfile"] = {
                "totalReports": 3,
                "totalPoints": 150,
                "level": "eco_warrior",
                "badges": ["first_report", "weekend_warrior"],
                "languagePreference": "en",
                "notificationPreferences": ["push", "sms"]
            }
        
        # Ensure location exists
        if "location" not in user:
            user["location"] = {
                "state": "Andhra Pradesh",
                "city": "Yanamalakuduru", 
                "pincode": "521456",
                "address": "123 Green Street, Yanamalakuduru, AP"
            }
        
        # Ensure basic fields exist
        if "reputation" not in user:
            user["reputation"] = 5.0
        
        if "isActive" not in user:
            user["isActive"] = True
        
        if "isVerified" not in user:
            user["isVerified"] = True
            
        if "emailVerified" not in user:
            user["emailVerified"] = True
            
        if "phoneVerified" not in user:
            user["phoneVerified"] = True
        
        if "phone" not in user:
            user["phone"] = "+91-9876543210"
            
        if "profilePicture" not in user:
            user["profilePicture"] = None
        
        return user
    
    # ===================
    # ENHANCED PROFILE MANAGEMENT
    # ===================
    
    async def update_citizen_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Enhanced citizen profile update with validation"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                print("âš ï¸ Database not available for profile update - using demo mode")
                return True  # Return success for demo mode
            
            print(f"ðŸ“ Updating profile for user: {user_id}")
            print(f"ðŸ“„ Update data: {update_data}")
            
            # Prepare update data with validation
            update_fields = {
                "updatedAt": datetime.utcnow()
            }
            
            # Handle basic profile fields
            if "fullName" in update_data:
                if len(update_data["fullName"].strip()) >= 2:
                    update_fields["fullName"] = update_data["fullName"].strip()
                else:
                    raise ValueError("Full name must be at least 2 characters")
            
            if "phone" in update_data:
                phone = update_data["phone"].strip()
                import re
                if re.match(r'^\+91-\d{10}$', phone):
                    update_fields["phone"] = phone
                else:
                    raise ValueError("Phone must be in format +91-XXXXXXXXXX")
            
            # Handle location data
            if "location" in update_data:
                location_data = update_data["location"]
                location_update = {}
                
                # Validate and update location fields
                if "state" in location_data and location_data["state"]:
                    location_update["location.state"] = location_data["state"].strip()
                
                if "city" in location_data and location_data["city"]:
                    location_update["location.city"] = location_data["city"].strip()
                
                if "pincode" in location_data and location_data["pincode"]:
                    pincode = location_data["pincode"].strip()
                    if re.match(r'^\d{6}$', pincode):
                        location_update["location.pincode"] = pincode
                    else:
                        raise ValueError("Pincode must be 6 digits")
                
                if "address" in location_data and location_data["address"]:
                    location_update["location.address"] = location_data["address"].strip()
                
                # Add location updates
                update_fields.update(location_update)
            
            # Handle citizen profile updates
            if "citizenProfile" in update_data:
                citizen_profile = update_data["citizenProfile"]
                
                # Language preference
                if "languagePreference" in citizen_profile:
                    valid_languages = ["en", "hi", "te", "ta", "bn"]
                    if citizen_profile["languagePreference"] in valid_languages:
                        update_fields["citizenProfile.languagePreference"] = citizen_profile["languagePreference"]
                    else:
                        raise ValueError("Invalid language preference")
                
                # Notification preferences
                if "notificationPreferences" in citizen_profile:
                    valid_notifications = ["push", "sms", "email"]
                    prefs = citizen_profile["notificationPreferences"]
                    if isinstance(prefs, list) and all(p in valid_notifications for p in prefs):
                        update_fields["citizenProfile.notificationPreferences"] = prefs
                    else:
                        raise ValueError("Invalid notification preferences")
            
            # Handle profile picture
            if "profilePicture" in update_data:
                update_fields["profilePicture"] = update_data["profilePicture"]
            
            # Handle account status updates
            if "isActive" in update_data:
                update_fields["isActive"] = bool(update_data["isActive"])
            
            if "deactivatedAt" in update_data:
                update_fields["deactivatedAt"] = update_data["deactivatedAt"]
            
            if "deactivationReason" in update_data:
                update_fields["deactivationReason"] = update_data["deactivationReason"]
            
            print(f"ðŸ’¾ Final update fields: {update_fields}")
            
            # Perform database update
            result = await self.database.users.update_one(
                {"_id": ObjectId(user_id), "role": "citizen"},
                {"$set": update_fields}
            )
            
            success = result.modified_count > 0
            print(f"âœ… Database update result: {success} (modified: {result.modified_count})")
            
            return success
            
        except ValueError as ve:
            print(f"âŒ Validation error: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            print(f"âŒ Error updating citizen profile: {e}")
            return False
    
    async def get_citizen_profile_complete(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete citizen profile with enhanced details"""
        try:
            user = await self.get_citizen_by_id(user_id)
            
            if not user:
                return None
            
            # Add calculated fields
            profile = {
                **user,
                "profileCompleteness": self.calculate_profile_completeness(user),
                "nextLevelProgress": self.calculate_level_progress(user),
                "monthlyStats": await self.get_monthly_stats(user_id),
                "recentBadges": self.get_recent_badges(user),
                "environmentalImpact": await self.calculate_environmental_impact(user_id)
            }
            
            return profile
            
        except Exception as e:
            print(f"âŒ Error getting complete profile: {e}")
            return None
    
    def calculate_profile_completeness(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate profile completion percentage"""
        try:
            required_fields = [
                "fullName", "email", "phone", 
                "location.state", "location.city", "location.pincode", "location.address"
            ]
            
            completed = 0
            total = len(required_fields)
            
            for field in required_fields:
                if "." in field:
                    # Nested field check
                    keys = field.split(".")
                    value = user
                    for key in keys:
                        value = value.get(key, "") if value else ""
                else:
                    value = user.get(field, "")
                
                if value and str(value).strip():
                    completed += 1
            
            percentage = int((completed / total) * 100)
            
            return {
                "percentage": percentage,
                "completed": completed,
                "total": total,
                "missingFields": [field for field in required_fields if not self._has_field_value(user, field)]
            }
            
        except Exception as e:
            print(f"âŒ Error calculating profile completeness: {e}")
            return {"percentage": 80, "completed": 6, "total": 7, "missingFields": []}
    
    def _has_field_value(self, user: Dict[str, Any], field: str) -> bool:
        """Check if a field has a value (including nested fields)"""
        try:
            if "." in field:
                keys = field.split(".")
                value = user
                for key in keys:
                    value = value.get(key, "") if value else ""
            else:
                value = user.get(field, "")
            
            return bool(value and str(value).strip())
        except:
            return False
    
    def calculate_level_progress(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate progress to next level"""
        try:
            current_points = user["citizenProfile"]["totalPoints"]
            current_level = user["citizenProfile"]["level"]
            
            # Define level thresholds
            level_thresholds = {
                "eco_rookie": {"min": 0, "max": 100, "next": "eco_warrior"},
                "eco_warrior": {"min": 100, "max": 300, "next": "waste_warrior"},
                "waste_warrior": {"min": 300, "max": 600, "next": "green_guardian"},
                "green_guardian": {"min": 600, "max": 1000, "next": "eco_champion"},
                "eco_champion": {"min": 1000, "max": float('inf'), "next": "max_level"}
            }
            
            level_info = level_thresholds.get(current_level, level_thresholds["eco_rookie"])
            
            if level_info["next"] == "max_level":
                return {
                    "currentLevel": current_level,
                    "nextLevel": "Max Level Reached",
                    "progress": 100,
                    "pointsToNext": 0,
                    "currentPoints": current_points
                }
            
            points_to_next = level_info["max"] - current_points
            progress = int(((current_points - level_info["min"]) / (level_info["max"] - level_info["min"])) * 100)
            
            return {
                "currentLevel": current_level,
                "nextLevel": level_info["next"],
                "progress": max(0, min(100, progress)),
                "pointsToNext": max(0, points_to_next),
                "currentPoints": current_points
            }
            
        except Exception as e:
            print(f"âŒ Error calculating level progress: {e}")
            return {
                "currentLevel": "eco_warrior",
                "nextLevel": "waste_warrior", 
                "progress": 50,
                "pointsToNext": 150,
                "currentPoints": 150
            }
    
    async def get_monthly_stats(self, user_id: str) -> Dict[str, Any]:
        """Get current month statistics"""
        try:
            # TODO: Implement actual monthly stats from database
            return {
                "reportsThisMonth": 8,
                "pointsThisMonth": 200,
                "rankThisMonth": 3,
                "goalProgress": 80,  # Percentage of monthly goal
                "streakDays": 5
            }
        except Exception as e:
            print(f"âŒ Error getting monthly stats: {e}")
            return {"reportsThisMonth": 0, "pointsThisMonth": 0, "rankThisMonth": 0, "goalProgress": 0, "streakDays": 0}
    
    def get_recent_badges(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recently earned badges"""
        try:
            badges = user["citizenProfile"].get("badges", [])
            
            # Demo badge data with timestamps
            badge_details = {
                "first_report": {
                    "name": "First Report",
                    "description": "Submitted your first waste report",
                    "icon": "ðŸŽ¯",
                    "earnedAt": "2025-01-15"
                },
                "weekend_warrior": {
                    "name": "Weekend Warrior",
                    "description": "Reported waste on a weekend",
                    "icon": "âš¡",
                    "earnedAt": "2025-01-20"
                },
                "sharp_eye": {
                    "name": "Sharp Eye",
                    "description": "Accurate waste type identification",
                    "icon": "ðŸ‘ï¸",
                    "earnedAt": "2025-01-18"
                }
            }
            
            recent_badges = []
            for badge_id in badges[-3:]:  # Get last 3 badges
                if badge_id in badge_details:
                    recent_badges.append(badge_details[badge_id])
            
            return recent_badges
            
        except Exception as e:
            print(f"âŒ Error getting recent badges: {e}")
            return []
    
    async def calculate_environmental_impact(self, user_id: str) -> Dict[str, Any]:
        """Calculate environmental impact metrics"""
        try:
            # TODO: Implement actual impact calculation from reports
            return {
                "co2Saved": 125.5,  # kg CO2
                "wasteRecycled": 45.2,  # kg
                "treesEquivalent": 3.2,  # trees saved
                "waterSaved": 2150  # liters
            }
        except Exception as e:
            print(f"âŒ Error calculating environmental impact: {e}")
            return {"co2Saved": 0, "wasteRecycled": 0, "treesEquivalent": 0, "waterSaved": 0}
    
    # ===================
    # STATISTICS & ANALYTICS
    # ===================
    
    async def get_citizen_stats(self, user_id: str) -> Dict[str, Any]:
        """Get citizen statistics"""
        try:
            user = await self.get_citizen_by_id(user_id)
            
            if not user:
                return {
                    "totalReports": 0,
                    "totalPoints": 0,
                    "level": "eco_rookie",
                    "reputation": 5.0,
                    "badges": []
                }
            
            return {
                "totalReports": user["citizenProfile"]["totalReports"],
                "totalPoints": user["citizenProfile"]["totalPoints"],
                "level": user["citizenProfile"]["level"],
                "reputation": user["reputation"],
                "badges": user["citizenProfile"].get("badges", [])
            }
            
        except Exception as e:
            print(f"âŒ Error getting citizen stats: {e}")
            return {
                "totalReports": 0,
                "totalPoints": 0,
                "level": "eco_rookie",
                "reputation": 5.0,
                "badges": []
            }
    
    async def update_citizen_stats(self, user_id: str, stat_updates: Dict[str, Any]) -> bool:
        """Update citizen statistics (points, reports, etc.)"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return False
            
            update_fields = {"updatedAt": datetime.utcnow()}
            
            # Update citizen profile stats
            for key, value in stat_updates.items():
                if key in ["totalReports", "totalPoints", "level"]:
                    update_fields[f"citizenProfile.{key}"] = value
                elif key == "reputation":
                    update_fields["reputation"] = value
                elif key == "badges":
                    update_fields["citizenProfile.badges"] = value
            
            result = await self.database.users.update_one(
                {"_id": ObjectId(user_id), "role": "citizen"},
                {"$set": update_fields}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"âŒ Error updating citizen stats: {e}")
            return False
    
    async def add_citizen_badge(self, user_id: str, badge_id: str) -> bool:
        """Add a new badge to citizen profile"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return False
            
            # Add badge to array if not already present
            result = await self.database.users.update_one(
                {"_id": ObjectId(user_id), "role": "citizen"},
                {
                    "$addToSet": {"citizenProfile.badges": badge_id},
                    "$set": {"updatedAt": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"âŒ Error adding badge: {e}")
            return False
    
    async def increment_citizen_points(self, user_id: str, points: int, reason: str = "") -> bool:
        """Increment citizen points and check for level up"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return False
            
            # Get current user data
            user = await self.get_citizen_by_id(user_id)
            if not user:
                return False
            
            current_points = user["citizenProfile"]["totalPoints"]
            new_points = current_points + points
            
            # Check for level up
            new_level = self.calculate_level_from_points(new_points)
            old_level = user["citizenProfile"]["level"]
            
            update_fields = {
                "citizenProfile.totalPoints": new_points,
                "updatedAt": datetime.utcnow()
            }
            
            # Update level if changed
            if new_level != old_level:
                update_fields["citizenProfile.level"] = new_level
                print(f"ðŸŽ‰ Level up! {old_level} â†’ {new_level}")
            
            result = await self.database.users.update_one(
                {"_id": ObjectId(user_id), "role": "citizen"},
                {"$set": update_fields}
            )
            
            # Log points transaction
            await self.log_points_transaction(user_id, points, reason, new_points)
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"âŒ Error incrementing points: {e}")
            return False
    
    def calculate_level_from_points(self, points: int) -> str:
        """Calculate level based on points"""
        if points < 100:
            return "eco_rookie"
        elif points < 300:
            return "eco_warrior"
        elif points < 600:
            return "waste_warrior"
        elif points < 1000:
            return "green_guardian"
        else:
            return "eco_champion"
    
    async def log_points_transaction(self, user_id: str, points: int, reason: str, new_total: int):
        """Log points transaction for history"""
        try:
            if self.database is None:
                return
            
            transaction = {
                "userId": ObjectId(user_id),
                "points": points,
                "reason": reason,
                "newTotal": new_total,
                "timestamp": datetime.utcnow()
            }
            
            await self.database.points_transactions.insert_one(transaction)
            
        except Exception as e:
            print(f"âŒ Error logging points transaction: {e}")
    
    # ===================
    # SERVICE REQUESTS (Future Implementation)
    # ===================
    
    async def get_citizen_requests(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get citizen's service requests - FIXED VERSION"""
        try:
            # Initialize database if not done
            if not hasattr(self, 'database') or self.database is None:
                await self.initialize()
            
            # 🔥 FIX: Check database properly without using bool()
            try:
                from ..shared.database import database
                # Check if database instance exists and is connected
                if (hasattr(database, 'database') and 
                    database.database is not None and 
                    hasattr(database, 'is_connected') and 
                    database.is_connected):
                    
                    print(f"✅ Database available - getting requests for user: {user_id}")
                    
                    # Query requests from database
                    cursor = database.database.requests.find({
                        "user_id": user_id
                    }).sort("created_at", -1).limit(limit)
                    
                    requests = await cursor.to_list(length=limit)
                    
                    # Process requests
                    for req in requests:
                        req["_id"] = str(req["_id"])
                        if not req.get("created_at"):
                            req["created_at"] = datetime.utcnow()
                    
                    print(f"✅ Found {len(requests)} requests from database")
                    return requests
                else:
                    print("⚠️ Database not available - returning empty list")
                    return []
                    
            except Exception as db_error:
                print(f"❌ Database query error: {db_error}")
                return []
                
        except Exception as e:
            print(f"❌ Service get_citizen_requests error: {e}")
            return []
    
    async def create_service_request(self, user_id: str, request_data: Dict[str, Any]) -> Optional[str]:
        """Create new service request"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return None
            
            # TODO: Implement service request creation
            # This will be the main feature we build next
            
            # For now, simulate request creation
            import random
            request_id = f"WR_2025_{random.randint(1000, 9999)}"
            
            print(f"ðŸ“ Created service request: {request_id}")
            return request_id
            
        except Exception as e:
            print(f"âŒ Error creating service request: {e}")
            return None
    
    # ===================
    # LEADERBOARD & COMMUNITY
    # ===================
    
    async def get_citizen_leaderboard(self, period: str = "weekly", limit: int = 10) -> List[Dict[str, Any]]:
        """Get citizen leaderboard"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                # Return demo leaderboard
                return [
                    {
                        "rank": 1,
                        "userId": "user_001",
                        "fullName": "Priya Sharma",
                        "points": 450,
                        "reports": 18,
                        "level": "eco_champion",
                        "avatar": "https://via.placeholder.com/40x40/22c55e/ffffff?text=PS"
                    },
                    {
                        "rank": 2,
                        "userId": "user_002",
                        "fullName": "Rajesh Kumar", 
                        "points": 420,
                        "reports": 16,
                        "level": "waste_warrior",
                        "avatar": "https://via.placeholder.com/40x40/3b82f6/ffffff?text=RK"
                    },
                    {
                        "rank": 3,
                        "userId": "demo_citizen_123",
                        "fullName": "Demo EcoWarrior",
                        "points": 150,
                        "reports": 3,
                        "level": "eco_warrior",
                        "avatar": "https://via.placeholder.com/40x40/f59e0b/ffffff?text=DE"
                    }
                ]
            
            # TODO: Implement actual leaderboard query
            # Based on period (weekly, monthly, all-time)
            # Sort by points/reports in descending order
            
            return []
            
        except Exception as e:
            print(f"âŒ Error getting leaderboard: {e}")
            return []
    
    async def get_citizen_rank(self, user_id: str, period: str = "weekly") -> Dict[str, Any]:
        """Get citizen's current rank"""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return {"rank": 3, "totalParticipants": 127, "percentile": 97.6}
            
            # TODO: Implement actual rank calculation
            return {"rank": 0, "totalParticipants": 0, "percentile": 0}
            
        except Exception as e:
            print(f"âŒ Error getting citizen rank: {e}")
            return {"rank": 0, "totalParticipants": 0, "percentile": 0}
    
    # ===================
    # ACHIEVEMENTS & BADGES
    # ===================
    
    async def check_and_award_badges(self, user_id: str) -> List[str]:
        """Check for new badge achievements and award them"""
        try:
            user = await self.get_citizen_by_id(user_id)
            if not user:
                return []
            
            current_badges = set(user["citizenProfile"].get("badges", []))
            new_badges = []
            
            # Define badge criteria
            badge_criteria = {
                "first_report": lambda u: u["citizenProfile"]["totalReports"] >= 1,
                "reporter_5": lambda u: u["citizenProfile"]["totalReports"] >= 5,
                "reporter_10": lambda u: u["citizenProfile"]["totalReports"] >= 10,
                "point_hunter_100": lambda u: u["citizenProfile"]["totalPoints"] >= 100,
                "point_hunter_500": lambda u: u["citizenProfile"]["totalPoints"] >= 500,
                "weekend_warrior": lambda u: True,  # TODO: Check if reported on weekend
                "sharp_eye": lambda u: u["reputation"] >= 4.5,
                "community_leader": lambda u: u["citizenProfile"]["totalReports"] >= 25,
                "eco_champion": lambda u: u["citizenProfile"]["level"] == "eco_champion"
            }
            
            # Check each badge criteria
            for badge_id, criteria_func in badge_criteria.items():
                if badge_id not in current_badges and criteria_func(user):
                    await self.add_citizen_badge(user_id, badge_id)
                    new_badges.append(badge_id)
                    print(f"ðŸ† New badge awarded: {badge_id}")
            
            return new_badges
            
        except Exception as e:
            print(f"âŒ Error checking badges: {e}")
            return []
    
    # ===================
    # PROFILE UTILITIES
    # ===================
    
    async def search_citizens(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search citizens by name, location, etc."""
        try:
            if self.database is None:
                await self.initialize()
            
            if self.database is None:
                return []
            
            search_filter = {
                "role": "citizen",
                "isActive": True,
                "$or": [
                    {"fullName": {"$regex": query, "$options": "i"}},
                    {"location.city": {"$regex": query, "$options": "i"}},
                    {"location.state": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Add additional filters
            if filters:
                if "minPoints" in filters:
                    search_filter["citizenProfile.totalPoints"] = {"$gte": filters["minPoints"]}
                if "level" in filters:
                    search_filter["citizenProfile.level"] = filters["level"]
                if "location" in filters:
                    search_filter["location.city"] = filters["location"]
            
            cursor = self.database.users.find(search_filter).limit(20)
            citizens = []
            
            async for user in cursor:
                user["_id"] = str(user["_id"])
                citizens.append({
                    "userId": user["_id"],
                    "fullName": user["fullName"],
                    "location": user["location"],
                    "level": user["citizenProfile"]["level"],
                    "points": user["citizenProfile"]["totalPoints"],
                    "reputation": user["reputation"]
                })
            
            return citizens
            
        except Exception as e:
            print(f"âŒ Error searching citizens: {e}")
            return []
    
    async def get_citizen_activity_feed(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get citizen's activity feed"""
        try:
            # TODO: Implement actual activity feed from database
            # This would include: reports submitted, badges earned, level ups, etc.
            
            demo_activities = [
                {
                    "id": "act_001",
                    "type": "report_submitted",
                    "title": "Waste Report Submitted",
                    "description": "Plastic waste reported at Park Street",
                    "timestamp": "2025-01-20T10:30:00Z",
                    "points": 25,
                    "icon": "ðŸ“"
                },
                {
                    "id": "act_002", 
                    "type": "badge_earned",
                    "title": "Badge Unlocked!",
                    "description": "Earned 'Sharp Eye' badge",
                    "timestamp": "2025-01-19T15:45:00Z",
                    "points": 50,
                    "icon": "ðŸ†"
                },
                {
                    "id": "act_003",
                    "type": "level_up",
                    "title": "Level Up!",
                    "description": "Advanced to Eco Warrior level",
                    "timestamp": "2025-01-18T12:00:00Z",
                    "points": 0,
                    "icon": "â¬†ï¸"
                }
            ]
            
            return demo_activities[:limit]
            
        except Exception as e:
            print(f"âŒ Error getting activity feed: {e}")
            return []
    
    # ===================
    # DATA VALIDATION UTILITIES
    # ===================
    
    def validate_citizen_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate citizen data"""
        errors = []
        
        try:
            # Required fields
            if not data.get("fullName") or len(data["fullName"].strip()) < 2:
                errors.append("Full name must be at least 2 characters")
            
            # Email validation
            email = data.get("email", "")
            if email:
                import re
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email):
                    errors.append("Invalid email format")
            
            # Phone validation
            phone = data.get("phone", "")
            if phone:
                if not re.match(r'^\+91-\d{10}, phone'):
                    errors.append("Phone must be in format +91-XXXXXXXXXX")
            
            # Location validation
            location = data.get("location", {})
            if location:
                if location.get("pincode") and not re.match(r'^\d{6}, location["pincode"]'):
                    errors.append("Pincode must be 6 digits")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors

# Global service instance
citizen_service = CitizenService()