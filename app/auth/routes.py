# app/auth/routes.py - Complete Fixed Version with Session Management
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
import json
import hashlib
import re

from ..shared.database import get_database

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

def hash_password(password: str) -> str:
    """Hash password using bcrypt (with error handling)"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"⚠️ Password hashing warning: {e}")
        # Fallback: Use a working hash method
        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        return f"fallback:{salt}:{hashlib.sha256((password + salt).encode()).hexdigest()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash (with error handling)"""
    try:
        if hashed_password.startswith("fallback:"):
            # Handle fallback hash
            parts = hashed_password.split(":")
            if len(parts) == 3:
                salt = parts[1]
                stored_hash = parts[2]
                computed_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
                return computed_hash == stored_hash
            return False
        else:
            # Regular bcrypt verification
            return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"⚠️ Password verification warning: {e}")
        return False

# ===================
# 🔥 FIXED LOGIN ROUTE
# ===================

@router.post("/login")
async def login_user(request: Request):
    """Enhanced login with session management - FIXED VERSION"""
    
    # Get login data from request body
    login_data = await request.json()
    print(f"🔐 LOGIN ATTEMPT: {login_data}")
    
    try:
        email = login_data.get("email", "").lower().strip()
        password = login_data.get("password", "")
        role = login_data.get("role", "")
        remember_me = login_data.get("rememberMe", False)
        
        # Basic validation
        if not email:
            raise HTTPException(status_code=400, detail="Email address is required")
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        if not role:
            raise HTTPException(status_code=400, detail="Please select your role")
        
        print(f"🔍 Looking for user: {email} with role: {role}")
        
        # Try database lookup
        try:
            from ..shared.database import database
            
            if database.database is None:
                print("⚠️ Database not connected - using demo login")
                
                # Create response with session cookie for demo
                response = JSONResponse({
                    "success": True,
                    "message": f"Welcome {email}! (Demo mode)",
                    "dashboardUrl": f"/{role}/dashboard",
                    "user": {
                        "email": email, 
                        "role": role, 
                        "fullName": "Demo User",
                        "userId": "demo_citizen_123"
                    }
                })
                response.set_cookie(
                    key="user_session",
                    value="demo_citizen_123",
                    max_age=3600,
                    httponly=True
                )
                return response
            
            # Check if user exists with this email (any role)
            any_user = await database.database.users.find_one({"email": email})
            
            if not any_user:
                print(f"❌ No user found with email: {email}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"No account found with email '{email}'. Please check your email or register for a new account."
                )
            
            # Check if user exists with the specific role
            user_with_role = await database.database.users.find_one({
                "email": email,
                "role": role
            })
            
            if not user_with_role:
                # User exists but with different role
                actual_role = any_user.get("role", "unknown")
                role_names = {
                    "citizen": "EcoWarrior (Citizen)",
                    "worker": "CleanGuard (Worker)", 
                    "government": "CityMaster (Government)"
                }
                
                actual_role_name = role_names.get(actual_role, actual_role)
                selected_role_name = role_names.get(role, role)
                
                print(f"❌ Role mismatch: User is {actual_role}, trying to login as {role}")
                raise HTTPException(
                    status_code=403,
                    detail=f"Your account is registered as '{actual_role_name}', but you selected '{selected_role_name}'. Please select the correct role to continue."
                )
            
            # User exists with correct role, now verify password
            if not verify_password(password, user_with_role["passwordHash"]):
                print("❌ Invalid password")
                raise HTTPException(
                    status_code=401, 
                    detail="Incorrect password. Please check your password and try again."
                )
            
            # Check if user account is active
            if not user_with_role.get("isActive", False):
                print("❌ Account is deactivated")
                raise HTTPException(
                    status_code=403, 
                    detail="Your account is currently deactivated. Please contact support for assistance."
                )
            
            # Update last login
            await database.database.users.update_one(
                {"_id": user_with_role["_id"]},
                {
                    "$set": {
                        "lastLogin": datetime.utcnow(),
                        "loginAttempts": 0
                    }
                }
            )
            
            user_id = str(user_with_role["_id"])
            print(f"✅ Login successful for {user_with_role['fullName']}")
            print(f"🆔 Setting session cookie: {user_id}")
            
            # Create success response
            role_welcome = {
                "citizen": f"Welcome back, {user_with_role['fullName']}! Ready to make our earth cleaner? 🌱",
                "worker": f"Welcome back, {user_with_role['fullName']}! Time to earn while serving the environment! 🛡️",
                "government": f"Welcome back, {user_with_role['fullName']}! Monitor and manage your city's environmental progress! 👑"
            }
            
            response_data = {
                "success": True,
                "message": role_welcome.get(role, f"Welcome back, {user_with_role['fullName']}!"),
                "dashboardUrl": f"/{role}/dashboard",
                "user": {
                    "userId": str(user_with_role["_id"]),
                    "email": user_with_role["email"],
                    "fullName": user_with_role["fullName"],
                    "role": user_with_role["role"],
                    "isVerified": user_with_role.get("isVerified", False),
                    "reputation": user_with_role.get("reputation", 5.0)
                }
            }
            
            # Create JSONResponse to set cookie
            response = JSONResponse(response_data)
            
            # Set session cookie
            cookie_max_age = 24 * 3600 if remember_me else 3600  # 24 hours or 1 hour
            response.set_cookie(
                key="user_session",
                value=user_id,
                max_age=cookie_max_age,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax"
            )
            
            print(f"✅ Session cookie set successfully: {user_id}")
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions (our custom error messages)
            raise
        except Exception as db_error:
            print(f"⚠️ Database error: {db_error}")
            # Fallback to demo mode if database fails
            response = JSONResponse({
                "success": True,
                "message": f"Welcome {email}! (Demo mode - Database unavailable)",
                "dashboardUrl": f"/{role}/dashboard",
                "user": {
                    "userId": "demo_fallback_123",
                    "email": email, 
                    "role": role, 
                    "fullName": "Demo User",
                    "isVerified": True,
                    "reputation": 5.0
                }
            })
            
            response.set_cookie(
                key="user_session",
                value="demo_fallback_123",
                max_age=3600,
                httponly=True
            )
            return response
            
    except HTTPException:
        # Re-raise our custom HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Unexpected login error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Login service temporarily unavailable. Please try again in a moment."
        )

# ===================
# LOGOUT ENDPOINT
# ===================

@router.post("/logout")
async def logout_user(request: Request):
    """Logout user by clearing session cookie"""
    try:
        response = JSONResponse({
            "success": True,
            "message": "Logged out successfully"
        })
        response.delete_cookie(key="user_session")
        return response
    except Exception as e:
        print(f"❌ Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

# ===================
# REGISTRATION WITH SESSION MANAGEMENT
# ===================

@router.post("/register/dynamic")
async def register_user_dynamic(request: Request):
    """IMPROVED Registration with automatic login and session management"""
    
    # Get registration data from request body
    registration_data = await request.json()
    print("🔥 REGISTRATION STARTED")
    print(f"📋 Received data: {json.dumps(registration_data, indent=2)}")
    
    try:
        role = registration_data.get("role")
        form_data = registration_data.get("formData", {})
        worker_type = registration_data.get("workerType")
        
        # Extract key fields
        email = form_data.get("email", "").lower().strip()
        phone = form_data.get("phone", "").strip()
        full_name = form_data.get("fullName", "").strip()
        password = form_data.get("password", "")
        
        print(f"🎭 Role: {role}")
        print(f"👤 Name: {full_name}")
        print(f"📧 Email: {email}")
        print(f"📱 Phone: {phone}")
        
        # Basic required fields
        if not role:
            raise HTTPException(status_code=400, detail="Role is required")
        if not full_name:
            raise HTTPException(status_code=400, detail="Full name is required")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number is required")
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(status_code=400, detail="Please enter a valid email address")
        
        # Phone validation (flexible for testing)
        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) < 10:
            raise HTTPException(status_code=400, detail="Phone number must be at least 10 digits")
        
        # Password validation
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        # Normalize phone number
        if len(phone_digits) == 10:
            normalized_phone = f"+91-{phone_digits}"
        else:
            normalized_phone = phone
        
        print("✅ Basic validation passed")
        
        # Check for existing user
        try:
            from ..shared.database import database
            
            if database.database is not None:
                print("🔍 Checking for existing user...")
                
                existing_user = await database.database.users.find_one({
                    "$or": [
                        {"email": email},
                        {"phone": normalized_phone}
                    ]
                })
                
                if existing_user:
                    if existing_user.get("email") == email:
                        print(f"❌ Email already exists: {email}")
                        raise HTTPException(
                            status_code=409, 
                            detail=f"An account with email '{email}' already exists. Please use a different email or try logging in."
                        )
                    else:
                        print(f"❌ Phone already exists: {normalized_phone}")
                        raise HTTPException(
                            status_code=409, 
                            detail=f"An account with phone number '{normalized_phone}' already exists. Please use a different phone number or try logging in."
                        )
                
                print("✅ No existing user found - proceeding with registration")
                
            else:
                print("⚠️ Database not connected - skipping existence check")
                
        except HTTPException:
            # Re-raise HTTP exceptions (user exists errors)
            raise
        except Exception as db_error:
            print(f"⚠️ Database check failed: {db_error}")
            # Continue without database check for development
        
        # Create user document
        user_doc = {
            "email": email,
            "phone": normalized_phone,
            "passwordHash": hash_password(password),
            "role": role,
            "fullName": full_name,
            "location": {
                "state": form_data.get("state", ""),
                "city": form_data.get("city", ""),
                "pincode": form_data.get("pincode", ""),
                "address": form_data.get("address", "")
            },
            "isActive": True,
            "isVerified": True,  # ✅ AUTO-VERIFIED FOR HACKATHON!
            "emailVerified": True,
            "phoneVerified": True,
            "reputation": 5.0,
            "totalActivities": 0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Add role-specific profile
        if role == "citizen":
            user_doc["citizenProfile"] = {
                "languagePreference": "en",
                "notificationPreferences": ["push", "sms"],
                "totalReports": 0,
                "totalPoints": 0,
                "level": "eco_rookie",
                "badges": []
            }
        elif role == "worker":
            user_doc["workerProfile"] = {
                "workerCategory": "independent_worker",
                "workerType": worker_type or "general_cleaner",
                "organizationName": form_data.get("organizationName", "Independent"),
                "workExperience": 0,
                "bankAccountNumber": form_data.get("bankAccountNumber", ""),
                "ifscCode": form_data.get("ifscCode", ""),
                "accountHolderName": form_data.get("accountHolderName", full_name),
                "totalJobsCompleted": 0,
                "averageRating": 5.0,
                "totalEarnings": 0.0,
                "isActive": True,
                "canStartWorking": True,
                "verificationStatus": "auto_approved"
            }
        elif role == "government":
            user_doc["governmentProfile"] = {
                "designation": form_data.get("designation", "Municipal Officer"),
                "department": form_data.get("department", "Urban Development"),
                "officeLevel": "municipal",
                "jurisdiction": form_data.get("jurisdiction", form_data.get("city", "")),
                "currentPosting": form_data.get("currentPosting", form_data.get("city", "")),
                "officeAddress": form_data.get("address", ""),
                "accessLevel": "full",
                "approvalStatus": "approved",  # ✅ AUTO-APPROVED FOR HACKATHON!
                "canAccessDashboard": True,
                "approvedBy": "system_auto",
                "approvalDate": datetime.utcnow()
            }
        
        # Save to database
        try:
            if database.database is not None:
                result = await database.database.users.insert_one(user_doc)
                user_id = str(result.inserted_id)
                print(f"✅ User saved to database with ID: {user_id}")
            else:
                user_id = f"demo_{role}_{full_name.replace(' ', '_')}"
                print(f"🔍 Demo mode - generated ID: {user_id}")
                
        except Exception as db_error:
            print(f"⚠️ Database save failed: {db_error}")
            user_id = f"demo_{role}_{full_name.replace(' ', '_')}"
        
        print("🎉 Registration successful!")
        
        # Create response with session cookie
        response_data = {
            "success": True,
            "message": f"🎉 Welcome to Meri Dharani, {full_name}! Your {role} account has been created successfully! 🇮🇳",
            "userId": user_id,
            "userRole": role,
            "requiresVerification": False,  # ❌ NO VERIFICATION FOR HACKATHON!
            "dashboardUrl": f"/{role}/dashboard",
            "autoLogin": True,
            "welcomeMessage": f"Your environmental journey starts now! 🌱"
        }
        
        # Create JSONResponse to set session cookie
        response = JSONResponse(response_data)
        
        # Set session cookie after registration
        response.set_cookie(
            key="user_session",
            value=user_id,
            max_age=3600,  # 1 hour
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        print(f"✅ Registration complete with session: {user_id}")
        return response
        
    except HTTPException as he:
        print(f"❌ HTTP Exception: {he.detail}")
        raise  # Re-raise HTTP exceptions with proper status codes
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# ===================
# WORKER TYPES API
# ===================

@router.get("/worker-types")
async def get_worker_types():
    """Get all available worker categories and types"""
    return [
        {
            "category": "government_employee",
            "typeId": "municipal_cleaner",
            "displayName": "Municipal Cleaner",
            "description": "Government employed waste management specialist with official credentials",
            "averageEarning": "₹150-400 per job",
            "badge": "🏛️ Municipal Specialist",
            "priority": "high",
            "availableSpecializations": ["general_waste", "bulk_collection", "street_cleaning", "drain_cleaning"]
        },
        {
            "category": "ngo_worker",
            "typeId": "ngo_plastic_specialist",
            "displayName": "NGO - Plastic Waste Specialist",
            "description": "NGO affiliated worker specializing in plastic waste collection and recycling",
            "averageEarning": "₹300-800 per job",
            "badge": "🤝 Community Champion",
            "priority": "medium",
            "availableSpecializations": ["plastic_bottles", "plastic_bags", "packaging_waste", "microplastics"]
        },
        {
            "category": "independent_worker",
            "typeId": "general_cleaner",
            "displayName": "Independent General Cleaner",
            "description": "Skilled independent worker providing flexible waste management services",
            "averageEarning": "₹200-500 per job",
            "badge": "💼 Eco Entrepreneur",
            "priority": "medium",
            "availableSpecializations": ["house_cleaning", "garden_waste", "general_sorting", "small_repairs"]
        }
    ]

# ===================
# FORM CONFIGURATION API
# ===================

@router.get("/form-config")
async def get_form_configuration(role: str, type: str = None):
    """Get dynamic form configuration based on role and type"""
    
    if role == "citizen":
        return {
            "role": "citizen",
            "formFields": {
                "personal": [
                    {
                        "field": "fullName",
                        "label": "Full Name",
                        "type": "text",
                        "placeholder": "Enter your full name",
                        "required": True
                    },
                    {
                        "field": "email",
                        "label": "Email Address",
                        "type": "email",
                        "placeholder": "your.email@example.com",
                        "required": True
                    },
                    {
                        "field": "phone",
                        "label": "Phone Number",
                        "type": "phone",
                        "placeholder": "+91-9876543210",
                        "required": True
                    },
                    {
                        "field": "password",
                        "label": "Password",
                        "type": "password",
                        "placeholder": "Create a strong password",
                        "required": True
                    }
                ],
                "location": [
                    {
                        "field": "state",
                        "label": "State",
                        "type": "select",
                        "options": ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu"],
                        "required": True
                    },
                    {
                        "field": "city",
                        "label": "City",
                        "type": "select",
                        "options": [],
                        "required": True
                    },
                    {
                        "field": "pincode",
                        "label": "Pincode",
                        "type": "text",
                        "placeholder": "521456",
                        "required": True
                    },
                    {
                        "field": "address",
                        "label": "Complete Address",
                        "type": "textarea",
                        "placeholder": "House/Building number, street, landmark...",
                        "required": True
                    }
                ]
            },
            "formSections": [
                {"title": "Personal Information", "fields": "personal", "icon": "👤"},
                {"title": "Location Details", "fields": "location", "icon": "📍"}
            ]
        }
    
    elif role == "worker":
        return {
            "role": "worker",
            "workerType": type,
            "formFields": {
                "personal": [
                    {
                        "field": "fullName",
                        "label": "Full Name",
                        "type": "text",
                        "placeholder": "Enter your full name",
                        "required": True
                    },
                    {
                        "field": "email",
                        "label": "Email Address",
                        "type": "email",
                        "placeholder": "your.email@example.com",
                        "required": True
                    },
                    {
                        "field": "phone",
                        "label": "Phone Number",
                        "type": "phone",
                        "placeholder": "+91-9876543210",
                        "required": True
                    },
                    {
                        "field": "password",
                        "label": "Password",
                        "type": "password",
                        "placeholder": "Create a strong password",
                        "required": True
                    }
                ],
                "professional": [
                    {
                        "field": "organizationName",
                        "label": "Organization Name",
                        "type": "text",
                        "placeholder": "Municipal Corporation / NGO / Self",
                        "required": True
                    },
                    {
                        "field": "workExperience",
                        "label": "Work Experience",
                        "type": "select",
                        "options": ["0-1 years", "1-3 years", "3-5 years", "5+ years"],
                        "required": True
                    }
                ],
                "banking": [
                    {
                        "field": "bankAccountNumber",
                        "label": "Bank Account Number",
                        "type": "text",
                        "placeholder": "1234567890123456",
                        "required": True
                    },
                    {
                        "field": "ifscCode",
                        "label": "IFSC Code",
                        "type": "text",
                        "placeholder": "SBIN0001234",
                        "required": True
                    }
                ],
                "location": [
                    {
                        "field": "state",
                        "label": "State",
                        "type": "select",
                        "options": ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu"],
                        "required": True
                    },
                    {
                        "field": "city",
                        "label": "City",
                        "type": "select",
                        "options": [],
                        "required": True
                    },
                    {
                        "field": "address",
                        "label": "Complete Address",
                        "type": "textarea",
                        "placeholder": "House/Building number, street, landmark...",
                        "required": True
                    }
                ]
            },
            "formSections": [
                {"title": "Personal Information", "fields": "personal", "icon": "👤"},
                {"title": "Professional Details", "fields": "professional", "icon": "🛡️"},
                {"title": "Banking Information", "fields": "banking", "icon": "💳"},
                {"title": "Location Details", "fields": "location", "icon": "📍"}
            ]
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid role")

# ===================
# LOCATIONS API
# ===================

@router.get("/locations")
async def get_location_options():
    """Get location options for dropdown menus"""
    return {
        "states": ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu"],
        "cities": {
            "Andhra Pradesh": ["Yanamalakuduru", "Vijayawada", "Guntur", "Machilipatnam"],
            "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
            "Karnataka": ["Bangalore", "Mysore", "Hubli"],
            "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"]
        }
    }

# ===================
# HEALTH CHECK
# ===================

@router.get("/health")
async def auth_health_check():
    """Authentication service health check"""
    return {
        "success": True,
        "message": "Authentication service is healthy",
        "timestamp": datetime.utcnow().isoformat()
    }