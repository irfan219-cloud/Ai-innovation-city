# app/shared/bin_service.py - Bin Management & Auto-Generation Service
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import random
import uuid
import math

from .database import get_database
from .config import settings

class BinManagementService:
    """Smart Bin Management with Auto-Generation for New Areas"""
    
    def __init__(self):
        self.db = None
        self.bins_collection = None
        self.users_collection = None
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if not self.db:
            self.db = await get_database()
            self.bins_collection = self.db.bins
            self.users_collection = self.db.users
    
    # ===================
    # BIN AUTO-GENERATION FOR NEW WORKERS
    # ===================
    
    async def create_bins_for_new_worker(self, worker_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Auto-generate bins when new CleanGuard registers in area"""
        try:
            await self._ensure_db_connection()
            
            worker_location = worker_data.get("location", {})
            area = worker_location.get("area", "Unknown Area")
            city = worker_location.get("city", "Vijayawada")
            
            print(f"🗑️ Auto-generating bins for new CleanGuard in: {area}, {city}")
            
            # Check if bins already exist in this area
            existing_bins = await self.bins_collection.count_documents({
                "location.area": area,
                "location.city": city
            })
            
            if existing_bins > 0:
                print(f"✅ Found {existing_bins} existing bins in {area}")
                return await self.get_bins_in_area(area, city)
            
            # Generate new bins for this area
            generated_bins = await self._generate_area_bins(worker_location)
            
            print(f"🎯 Generated {len(generated_bins)} new bins for {area}")
            return generated_bins
            
        except Exception as e:
            print(f"❌ Error creating bins for worker: {e}")
            return []
    
    async def _generate_area_bins(self, worker_location: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate realistic bins for worker's area"""
        area = worker_location.get("area", "Unknown Area")
        city = worker_location.get("city", "Vijayawada")
        pincode = worker_location.get("pincode", "521108")
        
        # Define bin placement strategy based on area type
        bin_count = self._calculate_optimal_bin_count(area)
        bin_locations = self._generate_bin_locations(worker_location, bin_count)
        
        generated_bins = []
        
        for i, location in enumerate(bin_locations):
            bin_data = {
                "bin_id": f"BIN_{city.upper()}_{area.replace(' ', '')[:3].upper()}_{str(i+1).zfill(3)}",
                "location": {
                    "area": area,
                    "city": city,
                    "pincode": pincode,
                    "landmark": location["landmark"],
                    "address": f"{location['landmark']}, {area}, {city}",
                    "coordinates": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"]
                    }
                },
                "bin_type": location["bin_type"],
                "capacity_liters": location["capacity"],
                "current_fill_level": 0,  # Start empty
                "last_collection_time": None,  # No collection yet
                "status": "active",  # Ready for use
                "waste_types": location["waste_types"],
                "collection_frequency": location["collection_frequency"],
                "priority_score": 0.5,  # Neutral priority initially
                "accessibility": {
                    "vehicle_access": location["vehicle_access"],
                    "pedestrian_access": True,
                    "collection_difficulty": location["difficulty"]
                },
                "maintenance": {
                    "condition": "good",  # New bins start in good condition
                    "last_maintenance": datetime.utcnow(),
                    "next_maintenance": datetime.utcnow() + timedelta(days=180)  # 6 months
                },
                "analytics": {
                    "avg_daily_waste": 0,  # Will be calculated from actual data
                    "peak_hours": location["peak_hours"],
                    "collection_efficiency": 1.0,  # Perfect initially
                    "total_collections": 0,
                    "total_waste_collected": 0
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "assigned_workers": [],  # Will be assigned dynamically
                "collection_history": []  # Starts empty, builds from real collections
            }
            
            generated_bins.append(bin_data)
        
        # Insert into database
        if generated_bins:
            await self.bins_collection.insert_many(generated_bins)
            print(f"✅ Inserted {len(generated_bins)} bins into database")
        
        return generated_bins
    
    def _calculate_optimal_bin_count(self, area: str) -> int:
        """Calculate optimal number of bins based on area type"""
        area_lower = area.lower()
        
        # Area type classification
        if any(word in area_lower for word in ["market", "commercial", "business", "shopping"]):
            return random.randint(15, 25)  # Commercial areas need more bins
        elif any(word in area_lower for word in ["residential", "colony", "nagar", "layout"]):
            return random.randint(8, 15)   # Residential areas
        elif any(word in area_lower for word in ["it", "tech", "park", "office"]):
            return random.randint(12, 20)  # IT/Tech areas
        elif any(word in area_lower for word in ["hospital", "school", "college", "university"]):
            return random.randint(10, 18)  # Institutional areas
        else:
            return random.randint(10, 16)  # Default for mixed areas
    
    def _generate_bin_locations(self, worker_location: Dict, bin_count: int) -> List[Dict[str, Any]]:
        """Generate realistic bin locations within area"""
        base_lat = float(worker_location.get("latitude", 16.5449))  # Default Vijayawada
        base_lng = float(worker_location.get("longitude", 81.5185))
        area = worker_location.get("area", "Unknown Area")
        
        locations = []
        
        # Common landmark types for different areas
        landmark_templates = [
            # Residential landmarks
            {"type": "residential", "names": ["Main Road Junction", "Community Center", "Local Market", "Bus Stop", "Temple Corner", "School Gate", "Apartment Complex", "Park Entrance"]},
            # Commercial landmarks  
            {"type": "commercial", "names": ["Shopping Complex", "Bank ATM", "Medical Store", "Restaurant Corner", "Office Building", "Petrol Pump", "Auto Stand", "Market Entrance"]},
            # Public landmarks
            {"type": "public", "names": ["Government Office", "Police Station", "Post Office", "Railway Station", "Bus Terminal", "Hospital Gate", "Park Corner", "Stadium Entrance"]}
        ]
        
        for i in range(bin_count):
            # Generate coordinates within 2km radius of worker location
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0.2, 2.0)  # 200m to 2km radius
            
            lat_offset = (distance / 111.0) * math.cos(angle)  # 1 degree lat ≈ 111km
            lng_offset = (distance / (111.0 * math.cos(math.radians(base_lat)))) * math.sin(angle)
            
            # Select landmark based on area type
            landmark_category = random.choice(landmark_templates)
            landmark = random.choice(landmark_category["names"])
            
            # Determine bin specifications
            bin_type, capacity, waste_types, frequency = self._determine_bin_specifications(landmark)
            
            location = {
                "landmark": f"{landmark} - {area}",
                "latitude": base_lat + lat_offset,
                "longitude": base_lng + lng_offset,
                "bin_type": bin_type,
                "capacity": capacity,
                "waste_types": waste_types,
                "collection_frequency": frequency,
                "vehicle_access": random.choice([True, True, False]),  # 66% vehicle accessible
                "difficulty": random.choice(["easy", "easy", "medium", "hard"]),
                "peak_hours": self._generate_peak_hours(landmark)
            }
            
            locations.append(location)
        
        return locations
    
    def _determine_bin_specifications(self, landmark: str) -> Tuple[str, int, List[str], str]:
        """Determine bin type and specifications based on landmark"""
        landmark_lower = landmark.lower()
        
        # High-capacity commercial bins
        if any(word in landmark_lower for word in ["market", "shopping", "complex", "restaurant"]):
            return (
                "commercial",
                1100,  # liters
                ["mixed", "plastic", "organic", "paper"],
                "twice_daily"
            )
        
        # Specialized bins
        elif any(word in landmark_lower for word in ["hospital", "medical"]):
            return (
                "medical",
                660,
                ["medical", "hazardous", "mixed"],
                "daily"
            )
        
        elif any(word in landmark_lower for word in ["office", "building", "it", "tech"]):
            return (
                "office",
                880,
                ["paper", "plastic", "e_waste", "mixed"],
                "daily"
            )
        
        # Standard residential bins
        else:
            return (
                "residential",
                660,
                ["mixed", "organic", "plastic"],
                "alternate_days"
            )
    
    def _generate_peak_hours(self, landmark: str) -> List[str]:
        """Generate peak waste generation hours based on landmark type"""
        landmark_lower = landmark.lower()
        
        if any(word in landmark_lower for word in ["market", "shopping"]):
            return ["10:00-12:00", "16:00-19:00"]  # Shopping hours
        elif any(word in landmark_lower for word in ["office", "building"]):
            return ["12:00-14:00", "18:00-20:00"]  # Lunch and evening
        elif any(word in landmark_lower for word in ["school", "college"]):
            return ["11:00-13:00", "15:00-17:00"]  # Break times
        elif any(word in landmark_lower for word in ["restaurant", "hotel"]):
            return ["13:00-15:00", "20:00-22:00"]  # Meal times
        else:
            return ["08:00-10:00", "18:00-20:00"]  # General residential
    
    # ===================
    # REAL-TIME BIN UPDATES (Dynamic from actual usage)
    # ===================
    
    async def update_bin_status_from_collection(self, bin_id: str, collection_data: Dict[str, Any]):
        """Update bin status after actual collection (REAL DATA)"""
        try:
            await self._ensure_db_connection()
            
            waste_collected = collection_data.get("waste_collected_kg", 0)
            collection_time = collection_data.get("collection_time", datetime.utcnow())
            worker_id = collection_data.get("worker_id")
            
            # Update bin with REAL collection data
            await self.bins_collection.update_one(
                {"bin_id": bin_id},
                {
                    "$set": {
                        "current_fill_level": 0,  # Empty after collection
                        "last_collection_time": collection_time,
                        "status": "normal",
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {
                        "analytics.total_collections": 1,
                        "analytics.total_waste_collected": waste_collected
                    },
                    "$push": {
                        "collection_history": {
                            "collection_id": f"COL_{str(uuid.uuid4())[:8].upper()}",
                            "collected_by": worker_id,
                            "collection_time": collection_time,
                            "waste_collected_kg": waste_collected,
                            "collection_duration_minutes": collection_data.get("duration_minutes", 0)
                        }
                    }
                }
            )
            
            # Recalculate analytics from REAL data
            await self._recalculate_bin_analytics(bin_id)
            
        except Exception as e:
            print(f"❌ Error updating bin from collection: {e}")
    
    async def update_bin_fill_level_from_reports(self, bin_id: str, reported_fill_level: int):
        """Update fill level from citizen reports (REAL DATA)"""
        try:
            await self._ensure_db_connection()
            
            # Determine status based on fill level
            if reported_fill_level > 90:
                status = "overflowing"
            elif reported_fill_level > 75:
                status = "needs_collection"
            else:
                status = "normal"
            
            await self.bins_collection.update_one(
                {"bin_id": bin_id},
                {
                    "$set": {
                        "current_fill_level": reported_fill_level,
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
        except Exception as e:
            print(f"❌ Error updating bin fill level: {e}")
    
    async def _recalculate_bin_analytics(self, bin_id: str):
        """Recalculate analytics from REAL collection history"""
        try:
            bin_data = await self.bins_collection.find_one({"bin_id": bin_id})
            if not bin_data:
                return
            
            history = bin_data.get("collection_history", [])
            if not history:
                return
            
            # Calculate REAL average daily waste from history
            if len(history) > 1:
                total_days = (history[0]["collection_time"] - history[-1]["collection_time"]).days
                total_waste = sum([h["waste_collected_kg"] for h in history])
                avg_daily_waste = total_waste / max(total_days, 1)
            else:
                avg_daily_waste = history[0]["waste_collected_kg"] if history else 0
            
            # Update with REAL calculated data
            await self.bins_collection.update_one(
                {"bin_id": bin_id},
                {
                    "$set": {
                        "analytics.avg_daily_waste": round(avg_daily_waste, 2)
                    }
                }
            )
            
        except Exception as e:
            print(f"❌ Error recalculating analytics: {e}")
    
    # ===================
    # SMART BIN PRIORITIZATION (Dynamic)
    # ===================
    
    async def get_priority_bins_for_collection(self, worker_location: Dict) -> List[Dict[str, Any]]:
        """Get bins that actually need collection (REAL priorities)"""
        try:
            await self._ensure_db_connection()
            
            area = worker_location.get("area")
            city = worker_location.get("city")
            
            # Get bins that ACTUALLY need collection
            priority_bins = await self.bins_collection.find({
                "location.area": area,
                "location.city": city,
                "$or": [
                    {"current_fill_level": {"$gte": 75}},  # 75%+ full
                    {"status": "needs_collection"},
                    {"status": "overflowing"},
                    {
                        "last_collection_time": {
                            "$lt": datetime.utcnow() - timedelta(days=2)  # Not collected in 2 days
                        }
                    }
                ]
            }).to_list(length=50)
            
            # Calculate REAL priority scores
            for bin_data in priority_bins:
                bin_data["_id"] = str(bin_data["_id"])
                bin_data["priority_score"] = self._calculate_real_priority(bin_data)
                bin_data["estimated_earnings"] = self._calculate_real_earnings(bin_data)
            
            # Sort by REAL priority
            priority_bins.sort(key=lambda x: x["priority_score"], reverse=True)
            
            return priority_bins
            
        except Exception as e:
            print(f"❌ Error getting priority bins: {e}")
            return []
    
    def _calculate_real_priority(self, bin_data: Dict) -> float:
        """Calculate REAL priority based on actual data"""
        score = 0.0
        
        # Fill level priority (0-40 points)
        fill_level = bin_data.get("current_fill_level", 0)
        score += (fill_level / 100) * 40
        
        # Time since last collection (0-30 points)
        last_collection = bin_data.get("last_collection_time")
        if last_collection:
            hours_since = (datetime.utcnow() - last_collection).total_seconds() / 3600
            score += min(30, hours_since / 24 * 10)  # Up to 30 points for 3+ days
        else:
            score += 30  # Never collected = high priority
        
        # Status urgency (0-20 points)
        status = bin_data.get("status", "normal")
        status_scores = {
            "overflowing": 20,
            "needs_collection": 15,
            "normal": 5,
            "maintenance": 0
        }
        score += status_scores.get(status, 5)
        
        # Historical average (0-10 points)
        avg_daily = bin_data.get("analytics", {}).get("avg_daily_waste", 0)
        score += min(10, avg_daily / 5)  # Higher for historically high-waste bins
        
        return round(score, 2)
    
    def _calculate_real_earnings(self, bin_data: Dict) -> int:
        """Calculate REAL earnings potential"""
        base_pay = 150
        
        # Fill level bonus
        fill_level = bin_data.get("current_fill_level", 0)
        fill_bonus = max(0, (fill_level - 50) * 2)
        
        # Bin type bonus
        bin_type = bin_data.get("bin_type", "residential")
        type_bonus = {
            "commercial": 50,
            "medical": 100,
            "office": 30,
            "residential": 0
        }.get(bin_type, 0)
        
        # Urgency bonus
        status = bin_data.get("status", "normal")
        urgency_bonus = {
            "overflowing": 100,
            "needs_collection": 50,
            "normal": 0
        }.get(status, 0)
        
        total = base_pay + fill_bonus + type_bonus + urgency_bonus
        return round(total)
    
    # ===================
    # BIN RETRIEVAL OPERATIONS
    # ===================
    
    async def get_bins_in_area(self, area: str, city: str) -> List[Dict[str, Any]]:
        """Get all bins in specific area"""
        try:
            await self._ensure_db_connection()
            
            bins = await self.bins_collection.find({
                "location.area": area,
                "location.city": city
            }).to_list(length=100)
            
            # Convert ObjectIds and add real-time data
            for bin_data in bins:
                bin_data["_id"] = str(bin_data["_id"])
                bin_data["heat_level"] = self._calculate_heat_level(bin_data)
                bin_data["estimated_earnings"] = self._calculate_collection_earnings(bin_data)
                bin_data["collection_urgency"] = self._calculate_urgency(bin_data)
            
            return bins
            
        except Exception as e:
            print(f"❌ Error getting bins in area: {e}")
            return []
    
    async def get_bins_for_worker(self, worker_id: str, radius_km: float = 5.0) -> List[Dict[str, Any]]:
        """Get bins within worker's coverage radius"""
        try:
            await self._ensure_db_connection()
            
            # Get worker location
            worker = await self.users_collection.find_one({"_id": ObjectId(worker_id)})
            if not worker:
                return []
            
            worker_location = worker.get("location", {})
            worker_area = worker_location.get("area")
            worker_city = worker_location.get("city")
            
            # Get bins in same area first
            bins = await self.get_bins_in_area(worker_area, worker_city)
            
            # Filter by additional criteria
            suitable_bins = []
            for bin_data in bins:
                if self._is_bin_suitable_for_worker(bin_data, worker):
                    suitable_bins.append(bin_data)
            
            return suitable_bins
            
        except Exception as e:
            print(f"❌ Error getting bins for worker: {e}")
            return []
    
    def _calculate_heat_level(self, bin_data: Dict) -> str:
        """Calculate heat map level for visualization"""
        fill_level = bin_data.get("current_fill_level", 0)
        last_collection = bin_data.get("last_collection_time")
        status = bin_data.get("status", "normal")
        
        # Critical status override
        if status in ["overflowing", "maintenance"]:
            return "red"
        
        # Time-based calculation
        if last_collection:
            hours_since = (datetime.utcnow() - last_collection).total_seconds() / 3600
            
            # Red: Very urgent (high fill + time)
            if fill_level > 80 or hours_since > 48:
                return "red"
            # Orange: Moderate urgency  
            elif fill_level > 60 or hours_since > 24:
                return "orange"
            # Green: Low priority
            else:
                return "green"
        else:
            # Never collected - status based on fill level only
            if fill_level > 75:
                return "red"
            elif fill_level > 50:
                return "orange"
            else:
                return "green"
    
    def _calculate_collection_earnings(self, bin_data: Dict) -> int:
        """Calculate earnings for bin collection"""
        return self._calculate_real_earnings(bin_data)
    
    def _calculate_urgency(self, bin_data: Dict) -> str:
        """Calculate collection urgency level"""
        priority_score = self._calculate_real_priority(bin_data)
        
        if priority_score >= 70:
            return "critical"
        elif priority_score >= 50:
            return "high"
        elif priority_score >= 30:
            return "medium"
        else:
            return "low"
    
    def _is_bin_suitable_for_worker(self, bin_data: Dict, worker: Dict) -> bool:
        """Check if bin is suitable for worker's specializations"""
        worker_specializations = worker.get("workerProfile", {}).get("specializations", [])
        bin_waste_types = bin_data.get("waste_types", [])
        
        # Check if worker can handle any of the bin's waste types
        return any(waste_type in worker_specializations for waste_type in bin_waste_types)

# Create global service instance
bin_management_service = BinManagementService()