# app/shared/request_service.py

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRequestService:
    """
    🚀 Enhanced Service Request Management
    Handles requests with AI timeline and user-specific views
    """
    
    def __init__(self, database, mitra_service):
        self.db = database
        self.mitra = mitra_service
        
        # Initialize collections
        self.requests_collection = "service_requests"
        self.user_requests_collection = "user_requests"
        self.timeline_collection = "request_timelines"
    
    async def create_service_request(
        self, 
        user_id: str, 
        description: str, 
        images: List[str] = None,
        user_type: str = "citizen",
        additional_data: Dict[str, Any] = None
    ) -> str:
        """Create new service request with AI-powered timeline"""
        
        try:
            # Generate unique request ID
            request_id = await self._generate_request_id()
            
            # Prepare request data
            request_data = {
                "request_id": request_id,
                "user_id": user_id,
                "user_type": user_type,
                "description": description,
                "images": images or [],
                "status": "submitted",
                "priority": "medium",
                "location": None,
                "waste_analysis": None,
                "assigned_worker": None,
                "estimated_completion": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                **(additional_data or {})
            }
            
            # Insert request into database
            await self.db[self.requests_collection].insert_one(request_data)
            logger.info(f"✅ Request created: {request_id}")
            
            # Update user's request tracking
            await self._update_user_requests(user_id, request_id, "add")
            
            # Initialize AI timeline
            await self._initialize_ai_timeline(request_id, user_id, user_type)
            
            # Start async processing pipeline
            asyncio.create_task(self._process_request_pipeline(request_id, request_data))
            
            return request_id
            
        except Exception as e:
            logger.error(f"❌ Request creation failed: {e}")
            raise Exception(f"Failed to create service request: {str(e)}")
    
    async def _generate_request_id(self) -> str:
        """Generate unique request ID like WR_2025_001"""
        try:
            year = datetime.now().year
            
            # Count requests for this year
            count = await self.db[self.requests_collection].count_documents({
                "request_id": {"$regex": f"^WR_{year}_"}
            })
            
            return f"WR_{year}_{str(count + 1).zfill(3)}"
            
        except Exception as e:
            logger.error(f"❌ ID generation failed: {e}")
            # Fallback to UUID
            return f"WR_{datetime.now().year}_{str(uuid.uuid4())[:8].upper()}"
    
    async def _update_user_requests(self, user_id: str, request_id: str, action: str):
        """Update user's request tracking record"""
        
        try:
            if action == "add":
                # Update or create user requests document
                await self.db[self.user_requests_collection].update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {
                            "total_requests": 1,
                            "active_requests": 1
                        },
                        "$push": {"request_ids": request_id},
                        "$set": {
                            "last_request_date": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    },
                    upsert=True  # Create if doesn't exist
                )
                
            elif action == "complete":
                await self.db[self.user_requests_collection].update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {
                            "active_requests": -1,
                            "completed_requests": 1
                        },
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                
            logger.info(f"✅ User requests updated: {user_id} - {action}")
            
        except Exception as e:
            logger.error(f"❌ User requests update failed: {e}")
    
    async def _initialize_ai_timeline(self, request_id: str, user_id: str, user_type: str):
        """Initialize AI timeline with first step"""
        
        try:
            # Generate first AI message
            ai_message = await self.mitra.generate_timeline_message(
                user_type=user_type,
                step="submitted",
                context={
                    "request_id": request_id,
                    "user_id": user_id
                }
            )
            
            # Create initial timeline step
            initial_step = {
                "step": "submitted",
                "timestamp": datetime.utcnow(),
                "ai_message": ai_message,
                "details": "Service request submitted by user",
                "user_visible": True,
                "worker_visible": False,
                "government_visible": True,
                "processing_time": 0.5
            }
            
            # Create timeline document
            timeline_doc = {
                "request_id": request_id,
                "user_id": user_id,
                "steps": [initial_step],
                "current_step": "submitted",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db[self.timeline_collection].insert_one(timeline_doc)
            logger.info(f"✅ Timeline initialized: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Timeline initialization failed: {e}")
    
    async def _process_request_pipeline(self, request_id: str, request_data: Dict[str, Any]):
        """Async processing pipeline for the request"""
        
        try:
            logger.info(f"🚀 Starting processing pipeline: {request_id}")
            
            # Step 1: AI Image Analysis (if images provided)
            if request_data.get("images"):
                await self._add_timeline_step(
                    request_id, 
                    "ai_analyzing", 
                    request_data["user_type"],
                    {"images_count": len(request_data["images"])}
                )
                
                # Simulate image analysis
                analysis_result = await self.mitra.analyze_waste_image(request_data["images"])
                await self._update_request_analysis(request_id, analysis_result)
            
            # Step 2: Worker Matching
            await asyncio.sleep(1.0)  # Realistic delay
            await self._add_timeline_step(
                request_id,
                "worker_matching",
                request_data["user_type"],
                {"location": request_data.get("location")}
            )
            
            # Step 3: Simulate worker assignment
            await asyncio.sleep(2.0)
            worker_data = await self._simulate_worker_assignment(request_id)
            
            await self._add_timeline_step(
                request_id,
                "worker_assigned", 
                request_data["user_type"],
                worker_data
            )
            
            # Update request status
            await self._update_request_status(request_id, "worker_assigned")
            
            logger.info(f"✅ Processing pipeline completed: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Processing pipeline failed: {e}")
            await self._add_timeline_step(
                request_id,
                "processing_error",
                request_data["user_type"], 
                {"error": str(e)}
            )
    
    async def _add_timeline_step(
        self, 
        request_id: str, 
        step: str, 
        user_type: str, 
        context: Dict[str, Any] = None
    ):
        """Add new step to request timeline"""
        
        try:
            # Generate AI message for this step
            ai_message = await self.mitra.generate_timeline_message(
                user_type=user_type,
                step=step,
                context=context or {}
            )
            
            # Define visibility for different user types
            visibility = self._get_step_visibility(step)
            
            # Create timeline step
            timeline_step = {
                "step": step,
                "timestamp": datetime.utcnow(),
                "ai_message": ai_message,
                "details": f"System processing: {step.replace('_', ' ').title()}",
                "context": context,
                "user_visible": visibility["user"],
                "worker_visible": visibility["worker"],
                "government_visible": visibility["government"],
                "processing_time": self._get_processing_time(step)
            }
            
            # Add to timeline
            await self.db[self.timeline_collection].update_one(
                {"request_id": request_id},
                {
                    "$push": {"steps": timeline_step},
                    "$set": {
                        "current_step": step,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"✅ Timeline step added: {request_id} - {step}")
            
        except Exception as e:
            logger.error(f"❌ Timeline step failed: {e}")
    
    def _get_step_visibility(self, step: str) -> Dict[str, bool]:
        """Define which users can see which steps"""
        
        visibility_map = {
            "submitted": {"user": True, "worker": False, "government": True},
            "ai_analyzing": {"user": True, "worker": False, "government": True},
            "worker_matching": {"user": True, "worker": True, "government": True},
            "worker_assigned": {"user": True, "worker": True, "government": True},
            "en_route": {"user": True, "worker": True, "government": True},
            "arrived": {"user": True, "worker": True, "government": True},
            "cleanup_started": {"user": True, "worker": True, "government": True},
            "completed": {"user": True, "worker": True, "government": True},
            "payment_processed": {"user": False, "worker": True, "government": True}
        }
        
        return visibility_map.get(step, {"user": True, "worker": True, "government": True})
    
    def _get_processing_time(self, step: str) -> float:
        """Get realistic processing time for each step"""
        
        processing_times = {
            "submitted": 0.5,
            "ai_analyzing": 2.5,
            "worker_matching": 1.5,
            "worker_assigned": 0.8,
            "en_route": 0.3,
            "arrived": 0.5,
            "cleanup_started": 0.5,
            "completed": 1.0,
            "payment_processed": 1.2
        }
        
        return processing_times.get(step, 0.5)
    
    async def _simulate_worker_assignment(self, request_id: str) -> Dict[str, Any]:
        """Simulate finding and assigning a worker"""
        
        # Mock worker data
        mock_workers = [
            {
                "worker_id": "CG_001",
                "name": "Ramesh Kumar",
                "category": "independent_worker",
                "rating": 4.7,
                "distance": "2.3 km",
                "eta": "45 minutes",
                "specialization": "plastic_waste",
                "estimated_earning": "₹300"
            },
            {
                "worker_id": "CG_002", 
                "name": "Priya Devi",
                "category": "ngo_worker",
                "rating": 4.9,
                "distance": "1.8 km", 
                "eta": "35 minutes",
                "specialization": "organic_waste",
                "estimated_earning": "₹250"
            }
        ]
        
        # Select random worker
        import random
        selected_worker = random.choice(mock_workers)
        
        # Update request with worker assignment
        await self.db[self.requests_collection].update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "assigned_worker": selected_worker,
                    "status": "worker_assigned",
                    "estimated_completion": datetime.utcnow() + timedelta(hours=1),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return selected_worker
    
    async def _update_request_analysis(self, request_id: str, analysis: Dict[str, Any]):
        """Update request with AI analysis results"""
        
        await self.db[self.requests_collection].update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "waste_analysis": analysis,
                    "priority": analysis.get("priority", "medium"),
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    async def _update_request_status(self, request_id: str, status: str):
        """Update request status"""
        
        await self.db[self.requests_collection].update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    async def get_user_requests(
        self, 
        user_id: str, 
        user_type: str = "citizen",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's requests with timeline"""
        
        try:
            # Get requests
            requests = await self.db[self.requests_collection].find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit).to_list(length=limit)
            
            # Get timelines for each request
            for request in requests:
                timeline = await self.get_request_timeline(
                    request["request_id"], 
                    user_type
                )
                request["timeline"] = timeline
            
            return requests
            
        except Exception as e:
            logger.error(f"❌ Get user requests failed: {e}")
            return []
    
    async def get_request_timeline(
        self, 
        request_id: str, 
        user_type: str = "citizen"
    ) -> List[Dict[str, Any]]:
        """Get timeline for specific request and user type"""
        
        try:
            timeline_doc = await self.db[self.timeline_collection].find_one(
                {"request_id": request_id}
            )
            
            if not timeline_doc:
                return []
            
            # Filter steps based on user type visibility
            visibility_key = f"{user_type}_visible"
            filtered_steps = [
                step for step in timeline_doc["steps"]
                if step.get(visibility_key, True)
            ]
            
            return filtered_steps
            
        except Exception as e:
            logger.error(f"❌ Get timeline failed: {e}")
            return []
    
    async def get_request_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get specific request by ID"""
        
        try:
            return await self.db[self.requests_collection].find_one(
                {"request_id": request_id}
            )
        except Exception as e:
            logger.error(f"❌ Get request failed: {e}")
            return None
    
    async def update_request_progress(
        self, 
        request_id: str, 
        step: str, 
        data: Dict[str, Any],
        user_type: str = "worker"
    ):
        """Update request progress (used by workers)"""
        
        try:
            # Add timeline step
            await self._add_timeline_step(request_id, step, user_type, data)
            
            # Update request status
            await self._update_request_status(request_id, step)
            
            # Handle completion
            if step == "completed":
                await self._handle_request_completion(request_id, data)
            
            logger.info(f"✅ Request progress updated: {request_id} - {step}")
            
        except Exception as e:
            logger.error(f"❌ Progress update failed: {e}")
            raise Exception(f"Failed to update progress: {str(e)}")
    
    async def _handle_request_completion(self, request_id: str, completion_data: Dict[str, Any]):
        """Handle request completion logic"""
        
        try:
            # Get request details
            request = await self.get_request_by_id(request_id)
            if not request:
                return
            
            # Update user's completed requests count
            await self._update_user_requests(request["user_id"], request_id, "complete")
            
            # Calculate environmental impact
            environmental_impact = await self._calculate_environmental_impact(completion_data)
            
            # Update request with final data
            await self.db[self.requests_collection].update_one(
                {"request_id": request_id},
                {
                    "$set": {
                        "status": "completed",
                        "completion_data": completion_data,
                        "environmental_impact": environmental_impact,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Add final timeline step with impact data
            await self._add_timeline_step(
                request_id,
                "impact_calculated",
                request["user_type"],
                environmental_impact
            )
            
            logger.info(f"✅ Request completion handled: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Completion handling failed: {e}")
    
    async def _calculate_environmental_impact(self, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate environmental impact of the cleanup"""
        
        try:
            # Extract data
            waste_collected = completion_data.get("waste_collected_kg", 0)
            waste_type = completion_data.get("waste_type", "mixed")
            recycled = completion_data.get("recycled", False)
            
            # Impact calculations (simplified)
            impact_factors = {
                "plastic": {"co2_per_kg": 2.5, "trees_per_kg": 0.1},
                "organic": {"co2_per_kg": 1.2, "trees_per_kg": 0.05},
                "e_waste": {"co2_per_kg": 4.0, "trees_per_kg": 0.2},
                "mixed": {"co2_per_kg": 2.0, "trees_per_kg": 0.08}
            }
            
            factors = impact_factors.get(waste_type, impact_factors["mixed"])
            
            co2_saved = waste_collected * factors["co2_per_kg"]
            trees_equivalent = waste_collected * factors["trees_per_kg"]
            
            # Bonus for recycling
            if recycled:
                co2_saved *= 1.5
                trees_equivalent *= 1.3
            
            return {
                "waste_collected_kg": waste_collected,
                "co2_saved_kg": round(co2_saved, 2),
                "trees_equivalent": round(trees_equivalent, 2),
                "water_saved_liters": round(waste_collected * 15, 1),
                "recycling_value": completion_data.get("recycling_value", 0),
                "environmental_score": round((co2_saved + trees_equivalent * 10), 1)
            }
            
        except Exception as e:
            logger.error(f"❌ Impact calculation failed: {e}")
            return {"error": str(e)}

# Database Structure Documentation
"""
📊 DATABASE COLLECTIONS STRUCTURE:

1. service_requests (Main requests collection)
{
    "_id": ObjectId(),
    "request_id": "WR_2025_001",
    "user_id": "user_123", 
    "user_type": "citizen",
    "description": "Plastic waste near park",
    "images": ["img1.jpg", "img2.jpg"],
    "status": "worker_assigned",
    "priority": "medium",
    "location": {
        "latitude": 16.5449,
        "longitude": 81.5185,
        "address": "Yanamalakuduru, Andhra Pradesh"
    },
    "waste_analysis": {
        "waste_type": "plastic",
        "confidence": 0.87,
        "quantity_estimate": "2.5 kg",
        "recyclable": true,
        "priority": "medium"
    },
    "assigned_worker": {
        "worker_id": "CG_001",
        "name": "Ramesh Kumar",
        "category": "independent_worker",
        "rating": 4.7,
        "distance": "2.3 km"
    },
    "environmental_impact": {
        "waste_collected_kg": 2.5,
        "co2_saved_kg": 6.25,
        "trees_equivalent": 0.25
    },
    "created_at": ISODate(),
    "updated_at": ISODate(),
    "completed_at": ISODate()
}

2. user_requests (User tracking collection)
{
    "_id": ObjectId(),
    "user_id": "user_123",
    "total_requests": 15,
    "active_requests": 2,
    "completed_requests": 13,
    "request_ids": ["WR_2025_001", "WR_2025_015", ...],
    "last_request_date": ISODate(),
    "created_at": ISODate(),
    "updated_at": ISODate()
}

3. request_timelines (Timeline collection)
{
    "_id": ObjectId(),
    "request_id": "WR_2025_001",
    "user_id": "user_123",
    "current_step": "worker_assigned",
    "steps": [
        {
            "step": "submitted",
            "timestamp": ISODate(),
            "ai_message": "🌱 MITRA: Request received! Dharani is proud!",
            "details": "Service request submitted by user",
            "context": {"user_name": "Priya"},
            "user_visible": true,
            "worker_visible": false,
            "government_visible": true,
            "processing_time": 0.5
        },
        {
            "step": "ai_analyzing", 
            "timestamp": ISODate(),
            "ai_message": "🤖 MITRA: Analyzing images... plastic detected!",
            "details": "AI processing waste images",
            "context": {"images_count": 2, "confidence": 0.87},
            "user_visible": true,
            "worker_visible": false,
            "government_visible": true,
            "processing_time": 2.5
        }
        // ... more steps
    ],
    "created_at": ISODate(),
    "updated_at": ISODate()
}

🔧 NOTIFICATION CHANNELS:

1. Real-time (WebSocket)
- Instant timeline updates
- Live progress tracking
- Worker status changes

2. Push Notifications (FCM)
- Critical updates
- Job assignments
- Completion alerts

3. SMS (Backup)
- Network connectivity issues
- Important status changes
- Payment confirmations

4. Email (Weekly/Monthly)
- Summary reports
- Impact statistics
- Achievement notifications

📱 USER TYPE SPECIFIC VIEWS:

EcoWarrior (Citizen) sees:
- Request submission confirmation
- AI analysis progress
- Worker assignment details
- Cleanup progress
- Environmental impact results

CleanGuard (Worker) sees:
- Job availability alerts
- Navigation assistance
- Documentation requirements
- Payment processing
- Performance ratings

CityMaster (Government) sees:
- All system activities
- Performance analytics
- Resource allocation
- Budget tracking
- Policy recommendations
"""

# Initialize global service
enhanced_request_service = None

async def get_enhanced_request_service():
    """Get or create enhanced request service instance"""
    global enhanced_request_service
    
    if not enhanced_request_service:
        from .database import database
        from .mitra_ai_service import get_mitra_service
        
        db = database.database
        mitra = await get_mitra_service()
        
        enhanced_request_service = EnhancedRequestService(db, mitra)
        logger.info("✅ Enhanced Request Service initialized")
    
    return enhanced_request_service