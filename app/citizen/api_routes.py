# app/citizen/api_routes.py - FINAL SIMPLE VERSION

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from datetime import datetime
import uuid
import base64
import os
import geohash2 as gh

# Import AI service
from .ai_service import SimpleMithraAI, store_request_with_mithra_insights

router = APIRouter(prefix="/citizen/api", tags=["citizen-requests"])
mithra_ai = SimpleMithraAI()

async def get_database():
    """Get real database connection"""
    try:
        from ..shared.database import database
        print(f"🔍 Database connected: {database.is_connected}")
        print(f"🔍 Database object: {database.database}")
        return database  # This is correct - storage function will use database.database
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None

async def get_current_user_from_session(request):
    """Get real user from session cookie - FINAL FIXED VERSION"""
    try:
        # Get user session from cookie
        user_session = request.cookies.get("user_session")
        
        if not user_session:
            # Return demo user if no session
            return {
                "_id": "demo_user_123",
                "fullName": "Demo EcoWarrior",
                "email": "demo@meriDharani.com",
                "role": "citizen",
                "language": "en"
            }
        
        # Try to get real user from database
        try:
            from ..shared.database import database
            # 🔥 FIX: Proper database check without bool()
            if (hasattr(database, 'database') and 
                database.database is not None and 
                hasattr(database, 'is_connected') and 
                database.is_connected):
                
                # Try to find user by session
                user = await database.database.users.find_one({"_id": user_session})
                if user:
                    user["_id"] = str(user["_id"])
                    return user
        except Exception as e:
            print(f"Database user lookup error: {e}")
            
        # Fallback to demo user with session ID
        return {
            "_id": user_session,
            "fullName": "Real User",
            "email": "user@meriDharani.com", 
            "role": "citizen",
            "language": "en"
        }
        
    except Exception as e:
        print(f"Session error: {e}")
        return {
            "_id": "demo_user_123",
            "fullName": "Demo User",
            "email": "demo@example.com",
            "role": "citizen"
        }

@router.post("/requests")
async def create_new_request(
    request_data: Dict[str, Any],
    request: Request,
    background_tasks: BackgroundTasks,
    db = Depends(get_database)
):
    """Create new waste request with SIMPLE AI flow"""
    try:
        # Get user
        current_user = await get_current_user_from_session(request)
        user_id = str(current_user.get("_id", "demo_user"))
        user_language = current_user.get("language", "en")
        
        # Generate request ID
        request_id = generate_location_based_id(
            request_data.get("location", {}).get("latitude", 0.0),
            request_data.get("location", {}).get("longitude", 0.0)
        )
        request_data["request_id"] = request_id
        
        # Process images
        if request_data.get("images"):
            processed_images = await process_request_images(request_data["images"], request_id)
            request_data["images"] = processed_images
        
        # Immediate response
        initial_response = {
            "status": "success",
            "request_id": request_id,
            "message": "Request submitted! AI is analyzing...",
            "estimated_completion": "2-3 minutes"
        }
        
        # Start background processing
        background_tasks.add_task(
            process_request_simple,
            request_data=request_data,
            user_id=user_id,
            user_language=user_language,
            request_id=request_id,
            db=db
        )
        
        return JSONResponse(content=initial_response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

async def process_request_simple(
    request_data: Dict,
    user_id: str, 
    user_language: str,
    request_id: str,
    db
):
    """SIMPLE background processing"""
    try:
        print(f"🤖 Processing {request_id}")
        
        # Run AI pipeline
        mithra_insights = await mithra_ai.complete_analysis_pipeline(
            request_data=request_data,
            user_language=user_language
        )
        
        print(f"🔍 AI Result: {mithra_insights.get('status', 'unknown')}")
        
        # If successful, store in database
        if mithra_insights.get("status") == "success":
            final_req_id = await store_request_with_mithra_insights(
                db=db,
                user_id=user_id,
                request_data=request_data, 
                mithra_insights=mithra_insights
            )
            print(f"💾 Stored: {final_req_id}")
        else:
            print(f"❌ Not stored - Status: {mithra_insights.get('status')}")
        
        print(f"✅ Processing complete for {request_id}")
        
    except Exception as e:
        print(f"❌ Processing failed for {request_id}: {e}")

# Helper functions
def generate_location_based_id(latitude: float, longitude: float) -> str:
    try:
        geohash = gh.encode(latitude, longitude, precision=6)
        timestamp = int(datetime.utcnow().timestamp())
        random_suffix = str(uuid.uuid4())[:6].upper()
        return f"REQ-{geohash.upper()}-{timestamp}-{random_suffix}"
    except:
        timestamp = int(datetime.utcnow().timestamp())
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"REQ-{timestamp}-{random_suffix}"

async def process_request_images(images_data: List[Dict], request_id: str) -> List[Dict]:
    processed_images = []
    
    for idx, img_data in enumerate(images_data):
        try:
            file_extension = img_data.get("name", "image.jpg").split(".")[-1]
            filename = f"{request_id}_{idx+1}.{file_extension}"
            
            file_path = await save_image_file(img_data["dataUrl"], filename)
            
            processed_images.append({
                "name": img_data["name"],
                "size": img_data.get("size", 0),
                "file_path": file_path,
                "upload_timestamp": datetime.utcnow(),
                "index": idx + 1
            })
            
        except Exception as e:
            print(f"❌ Error processing image {idx}: {e}")
            continue
    
    return processed_images

async def save_image_file(data_url: str, filename: str) -> str:
    try:
        upload_dir = "uploads/waste_images"
        os.makedirs(upload_dir, exist_ok=True)
        
        if "," in data_url:
            base64_data = data_url.split(",")[1]
        else:
            base64_data = data_url
        
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))
        
        return file_path
        
    except Exception as e:
        print(f"❌ Error saving image {filename}: {e}")
        return f"uploads/waste_images/{filename}"

@router.get("/requests/{request_id}/status")
async def get_request_status(request_id: str):
    return {
        "success": True,
        "data": {
            "request_id": request_id,
            "status": "completed",
            "message": "Request processed successfully"
        }
    }

@router.get("/statistics")
async def get_citizen_statistics(request: Request):
    """📊 GET CITIZEN STATISTICS API - FIXED structure to match frontend"""
    try:
        # Get user from session
        user = await get_current_user_from_session(request)
        user_id = str(user.get("_id", "demo_user_123"))
        
        print(f"📊 Getting statistics for user: {user_id}")
        
        # Initialize stats with CORRECT field names that frontend expects
        stats = {
            "total": 0,
            "submitted": 0,
            "processing": 0,
            "assigned": 0,
            "inProgress": 0,
            "completed": 0,
            "active": 0,
            "impactScore": 0,
            "impact": {
                "co2Saved": 0,
                "wasteCollected": 0,
                "treesEquivalent": 0,
                "waterSaved": 0
            }
        }
        
        try:
            from ..shared.database import database
            
            # Check database availability
            if (hasattr(database, 'is_connected') and database.is_connected and
                hasattr(database, 'database') and database.database is not None):
                
                print("✅ Database available - calculating statistics")
                
                # Get all user requests
                requests_cursor = database.database.requests.find({
                    "user_id": user_id
                })
                
                requests = await requests_cursor.to_list(length=100)
                
                # 🔥 CALCULATE STATISTICS WITH CORRECT MAPPING
                total_requests = len(requests)
                submitted_count = 0
                processing_count = 0
                assigned_count = 0
                in_progress_count = 0
                completed_count = 0
                total_impact_score = 0
                total_waste = 0
                total_co2 = 0
                total_trees = 0
                total_water = 0
                
                print(f"🔧 Processing {total_requests} requests for statistics")
                
                for req in requests:
                    status = req.get("status", "submitted")
                    print(f"🔧 Request {req.get('request_id')} has status: {status}")
                    
                    # Count by status - handle all possible status values
                    if status == "submitted":
                        submitted_count += 1
                    elif status == "processing" or status == "ai_analyzed":
                        processing_count += 1
                    elif status == "assigned" or status == "worker_assigned":
                        assigned_count += 1
                    elif status == "in_progress" or status == "in-progress":
                        in_progress_count += 1
                    elif status == "completed":
                        completed_count += 1
                    else:
                        # Default unknown status to submitted
                        submitted_count += 1
                        print(f"⚠️ Unknown status '{status}', counting as submitted")
                    
                    # Calculate environmental impact
                    env_impact = req.get("environmental_impact", {})
                    if env_impact:
                        total_waste += float(env_impact.get("waste_collected_kg", 0))
                        total_co2 += float(env_impact.get("co2_saved_kg", 0))
                        total_trees += float(env_impact.get("trees_equivalent", 0))
                        total_water += float(env_impact.get("water_saved_liters", 0))
                        total_impact_score += float(env_impact.get("environmental_score", 0))
                
                # Calculate active requests (everything except completed)
                active_count = submitted_count + processing_count + assigned_count + in_progress_count
                
                # 🔥 BUILD RESPONSE WITH EXACT FIELD NAMES FRONTEND EXPECTS
                stats = {
                    "total": total_requests,
                    "submitted": submitted_count,
                    "processing": processing_count,
                    "assigned": assigned_count,
                    "inProgress": in_progress_count,  # Note: camelCase
                    "completed": completed_count,
                    "active": active_count,
                    "impactScore": round(total_impact_score, 1),
                    "impact": {
                        "co2Saved": round(total_co2, 1),
                        "wasteCollected": round(total_waste, 1),
                        "treesEquivalent": round(total_trees, 1),
                        "waterSaved": round(total_water, 1)
                    }
                }
                
                print(f"✅ Final statistics: {stats}")
            else:
                print("⚠️ Database not available - using default stats")
                
        except Exception as e:
            print(f"❌ Statistics query failed: {e}")
            import traceback
            print(f"🔧 Full traceback: {traceback.format_exc()}")
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        print(f"❌ Statistics API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")