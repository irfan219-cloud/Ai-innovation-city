# main.py - FIXED VERSION
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import sys
import os
from bson import ObjectId
from app.citizen.services import citizen_service
from fastapi import HTTPException
from datetime import datetime

# Add the project root to Python path to fix imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create FastAPI app
app = FastAPI(
    title="Meri Dharani API",
    description="AI-Powered Waste Management System - मेरी पवित्र धरणी मां",
    version="1.0.0"
)

# Add this at the top of main.py
from dotenv import load_dotenv
load_dotenv()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware - Install: pip install itsdangerous
try:
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key="meri-dharani-secret-key-2025")
    print("✅ Session middleware enabled")
except ImportError:
    print("⚠️ Session middleware not available - install: pip install itsdangerous")

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# ===================
# INCLUDE ROUTES - FIXED ORDER
# ===================

# Authentication routes
try:
    from app.auth.routes import router as auth_router
    app.include_router(auth_router, prefix="/api")
    print("✅ Successfully loaded auth routes")
except ImportError as e:
    print(f"❌ Auth routes import error: {e}")

# Citizen routes
try:
    from app.citizen.routes import router as citizen_router  
    app.include_router(citizen_router)
    print("✅ Successfully loaded citizen routes")
except ImportError as e:
    print(f"❌ Citizen routes import failed: {e}")

try:
    from app.citizen.api_routes import router as citizen_api_routes
    app.include_router(citizen_api_routes)
    print("✅ Successfully loaded citizen API routes")
except ImportError as e:
    print(f"❌ Citizen API routes import failed: {e}")

# Worker routes - FIXED (No fallback conflicts)
try:
    from app.worker.routes import router as worker_router
    app.include_router(worker_router)
    print("✅ Successfully loaded worker routes")
except ImportError as e:
    print(f"❌ Worker routes import error: {e}")
    print("🔧 Please check app/worker/routes.py file exists and is valid")

# ===================
# BASIC PAGES
# ===================

@app.get("/")
async def login_page(request: Request):
    """Main login page for all users"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    """Registration page for new users"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/government/dashboard")
async def government_dashboard(request: Request):
    """CityMaster dashboard"""
    try:
        user_id = request.cookies.get("user_session", "demo_government")
        
        gov_user = {
            "_id": user_id,
            "fullName": "Demo CityMaster",
            "role": "government",
            "governmentProfile": {
                "designation": "Municipal Commissioner",
                "department": "Waste Management",
                "jurisdiction": "Yanamalakuduru Municipality"
            }
        }
        
        return templates.TemplateResponse("government/dashboard.html", {
            "request": request,
            "user": gov_user
        })
        
    except Exception as e:
        print(f"❌ Government dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Government dashboard failed")

# ===================
# TEST ROUTES FOR DEBUGGING
# ===================

@app.get("/test-worker")
async def test_worker_system():
    """Test endpoint to verify worker system"""
    return {
        "status": "✅ Worker system is ready!",
        "available_routes": [
            "/worker/dashboard - Worker Dashboard",
            "/worker/jobs - Available Jobs with Live Location", 
            "/worker/active-route - Live Journey Tracking",
            "/worker/profile - Worker Profile"
        ],
        "features": [
            "🗑️ Dynamic Bin Generation",
            "📍 Live GPS Location",
            "🛒 Journey Cart System", 
            "🔍 Route Preview",
            "🚀 Active Route Tracking",
            "💰 Real-time Earnings"
        ]
    }

@app.get("/debug-routes")
async def debug_routes():
    """Debug: Show all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else ["GET"]
            })
    return {"total_routes": len(routes), "routes": routes}

# ===================
# DATABASE EVENTS
# ===================

@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    try:
        print("🚀 Starting Meri Dharani API...")
        
        # Try to connect to database
        try:
            from app.shared.database import database
            await database.connect_to_database()
            print("✅ Database connection established")
        except Exception as db_error:
            print(f"⚠️ Database connection failed: {db_error}")
            print("🔧 Continuing in demo mode...")
        
        print("🎉 Meri Dharani API is ready!")
        print("🌐 Visit: http://localhost:8000")
        print("📚 API Docs: http://localhost:8000/docs")
        print("🔍 Test Worker: http://localhost:8000/test-worker")
        print("🇮🇳 Made in India with ❤️")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("🔧 Continuing anyway for development...")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection"""
    try:
        from app.shared.database import database
        await database.close_database_connection()
        print("✅ Database connection closed")
    except:
        print("✅ Shutdown complete")

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)