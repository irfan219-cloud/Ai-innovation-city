# app/auth/services.py - Authentication Services
import hashlib
import secrets
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..shared.config import settings, get_firebase_config
from ..shared.database import get_users_collection, get_worker_types_collection
from ..shared.models import UserModel, WorkerTypeModel
from .schemas import *

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize Firebase Admin SDK (only if configured)
firebase_config = get_firebase_config()
if firebase_config:
    try:
        # Check if Firebase app is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize Firebase if not already done
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        print("âœ… Firebase initialized")
else:
    print("âš ï¸ Firebase not configured - using development mode")

class AuthService:
    """Authentication service with Firebase integration"""
    
    def __init__(self):
        self.users_collection = get_users_collection()
        self.worker_types_collection = get_worker_types_collection()
    
    # ===================
    # PASSWORD UTILITIES
    # ===================
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ===================
    # JWT TOKEN UTILITIES
    # ===================
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token (longer expiry)"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=30)  # 30 days
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            
            if payload.get("type") != token_type:
                return None
            
            return payload
        except JWTError:
            return None
    
    # ===================
    # OTP UTILITIES
    # ===================
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate numeric OTP"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    def generate_verification_token(self) -> str:
        """Generate secure verification token"""
        return secrets.token_urlsafe(32)
    
    # ===================
    # USER REGISTRATION
    # ===================
    
    async def register_citizen(self, registration_data: CitizenRegistrationSchema) -> Tuple[bool, str, Dict[str, Any]]:
        """Register new EcoWarrior (Citizen)"""
        try:
            # Check if user already exists
            existing_user = await self.users_collection.find_one({
                "$or": [
                    {"email": registration_data.email},
                    {"phone": registration_data.phone}
                ]
            })
            
            if existing_user:
                return False, "User with this email or phone already exists", {}
            
            # Create user model
            user_data = {
                "email": registration_data.email,
                "phone": registration_data.phone,
                "passwordHash": self.hash_password(registration_data.password),
                "role": "citizen",
                "fullName": registration_data.fullName,
                "location": registration_data.location.dict(),
                "citizenProfile": {
                    "languagePreference": registration_data.languagePreference,
                    "notificationPreferences": registration_data.notificationPreferences,
                    "totalReports": 0,
                    "totalPoints": 0,
                    "level": "eco_rookie",
                    "badges": []
                },
                "isActive": True,
                "isVerified": False,
                "emailVerified": False,
                "phoneVerified": False,
                "reputation": 5.0,
                "totalActivities": 0,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            
            # Insert user
            result = await self.users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            # Generate OTP for phone verification
            otp = self.generate_otp()
            await self.send_phone_otp(registration_data.phone, otp)
            
            return True, "Citizen registered successfully", {
                "userId": user_id,
                "requiresVerification": True,
                "dashboardUrl": "/citizen/dashboard"
            }
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}", {}
    
    async def register_worker(self, registration_data: WorkerRegistrationSchema) -> Tuple[bool, str, Dict[str, Any]]:
        """Register new CleanGuard (Worker)"""
        try:
            # Check if user already exists
            existing_user = await self.users_collection.find_one({
                "$or": [
                    {"email": registration_data.email},
                    {"phone": registration_data.phone}
                ]
            })
            
            if existing_user:
                return False, "User with this email or phone already exists", {}
            
            # Validate worker type exists
            worker_type = await self.worker_types_collection.find_one({
                "category": registration_data.workerCategory,
                "typeId": registration_data.workerType,
                "isActive": True
            })
            
            if not worker_type:
                return False, "Invalid worker type selected", {}
            
            # Process joining date
            joining_date = None
            if registration_data.joiningDate:
                try:
                    joining_date = datetime.fromisoformat(registration_data.joiningDate.replace('Z', '+00:00'))
                except:
                    joining_date = None
            
            # Create worker profile
            worker_profile = {
                "workerCategory": registration_data.workerCategory,
                "workerType": registration_data.workerType,
                "organizationName": registration_data.organizationName,
                "workExperience": registration_data.workExperience,
                "specializations": registration_data.specializations,
                "bankAccountNumber": registration_data.bankAccountNumber,
                "ifscCode": registration_data.ifscCode,
                "accountHolderName": registration_data.accountHolderName,
                "totalJobsCompleted": 0,
                "averageRating": 5.0,
                "totalEarnings": 0.0,
                "isActive": True,
                "canStartWorking": True,
                "verificationStatus": "auto_approved"
            }
            
            # Add optional fields based on worker category
            if registration_data.employeeId:
                worker_profile["employeeId"] = registration_data.employeeId
            if registration_data.department:
                worker_profile["department"] = registration_data.department
            if registration_data.designation:
                worker_profile["designation"] = registration_data.designation
            if registration_data.workingArea:
                worker_profile["workingArea"] = registration_data.workingArea
            if registration_data.organizationAddress:
                worker_profile["organizationAddress"] = registration_data.organizationAddress
            if registration_data.supervisorName:
                worker_profile["supervisorName"] = registration_data.supervisorName
            if registration_data.supervisorContact:
                worker_profile["supervisorContact"] = registration_data.supervisorContact
            if registration_data.workPermitNumber:
                worker_profile["workPermitNumber"] = registration_data.workPermitNumber
            if joining_date:
                worker_profile["joiningDate"] = joining_date
            if registration_data.currentSalary:
                worker_profile["currentSalary"] = registration_data.currentSalary
            
            # NGO specific fields
            if registration_data.workerCategory == "ngo_worker":
                if registration_data.ngoName:
                    worker_profile["ngoName"] = registration_data.ngoName
                if registration_data.ngoRegistrationNumber:
                    worker_profile["ngoRegistrationNumber"] = registration_data.ngoRegistrationNumber
                if registration_data.roleInNGO:
                    worker_profile["roleInNGO"] = registration_data.roleInNGO
            
            # Independent worker fields
            elif registration_data.workerCategory == "independent_worker":
                if registration_data.previousWorkType:
                    worker_profile["previousWorkType"] = registration_data.previousWorkType
                if registration_data.skillAreas:
                    worker_profile["skillAreas"] = registration_data.skillAreas
                if registration_data.ownEquipment:
                    worker_profile["ownEquipment"] = registration_data.ownEquipment
                if registration_data.equipmentDetails:
                    worker_profile["equipmentDetails"] = registration_data.equipmentDetails
                if registration_data.transportationMode:
                    worker_profile["transportationMode"] = registration_data.transportationMode
            
            # Work coverage
            if registration_data.workCoverage:
                worker_profile["workCoverage"] = registration_data.workCoverage.dict()
            
            # Create user model
            user_data = {
                "email": registration_data.email,
                "phone": registration_data.phone,
                "passwordHash": self.hash_password(registration_data.password),
                "role": "worker",
                "fullName": registration_data.fullName,
                "location": registration_data.location.dict(),
                "workerProfile": worker_profile,
                "isActive": True,
                "isVerified": False,
                "emailVerified": False,
                "phoneVerified": False,
                "reputation": 5.0,
                "totalActivities": 0,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            
            # Insert user
            result = await self.users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            # Generate OTP for phone verification
            otp = self.generate_otp()
            await self.send_phone_otp(registration_data.phone, otp)
            
            return True, "CleanGuard registered successfully", {
                "userId": user_id,
                "requiresVerification": True,
                "dashboardUrl": "/worker/dashboard"
            }
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}", {}
    
    async def register_government(self, registration_data: GovernmentRegistrationSchema) -> Tuple[bool, str, Dict[str, Any]]:
        """Register new CityMaster (Government Official)"""
        try:
            # Check if user already exists
            existing_user = await self.users_collection.find_one({
                "$or": [
                    {"email": registration_data.officialEmail},
                    {"phone": registration_data.phone}
                ]
            })
            
            if existing_user:
                return False, "User with this email or phone already exists", {}
            
            # Process posting date
            posting_date = None
            if registration_data.postingDate:
                try:
                    posting_date = datetime.fromisoformat(registration_data.postingDate.replace('Z', '+00:00'))
                except:
                    posting_date = None
            
            # Create government profile
            government_profile = {
                "designation": registration_data.designation,
                "department": registration_data.department,
                "officeLevel": registration_data.officeLevel,
                "jurisdiction": registration_data.jurisdiction,
                "currentPosting": registration_data.currentPosting,
                "officeAddress": registration_data.officeAddress,
                "accessLevel": "limited",
                "budgetAuthority": None,
                "areaAuthority": [],
                "approvalStatus": "pending_manual_review",
                "canAccessDashboard": False,
                "approvedBy": None,
                "approvalDate": None
            }
            
            # Add optional fields
            if registration_data.employeeCode:
                government_profile["employeeCode"] = registration_data.employeeCode
            if posting_date:
                government_profile["postingDate"] = posting_date
            if registration_data.officeContact:
                government_profile["officeContact"] = registration_data.officeContact
            if registration_data.secretaryName:
                government_profile["secretaryName"] = registration_data.secretaryName
            if registration_data.secretaryContact:
                government_profile["secretaryContact"] = registration_data.secretaryContact
            
            # Create user model
            user_data = {
                "email": registration_data.officialEmail,
                "phone": registration_data.phone,
                "passwordHash": self.hash_password(registration_data.password),
                "role": "government",
                "fullName": registration_data.fullName,
                "location": registration_data.location.dict(),
                "governmentProfile": government_profile,
                "isActive": False,  # Inactive until manual approval
                "isVerified": False,
                "emailVerified": False,
                "phoneVerified": False,
                "reputation": 5.0,
                "totalActivities": 0,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            
            # Store personal email if provided
            if registration_data.personalEmail:
                user_data["personalEmail"] = registration_data.personalEmail
            
            # Insert user
            result = await self.users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            
            # Generate OTP for phone verification
            otp = self.generate_otp()
            await self.send_phone_otp(registration_data.phone, otp)
            
            return True, "Government official registered successfully. Pending manual approval.", {
                "userId": user_id,
                "requiresVerification": True,
                "requiresApproval": True,
                "dashboardUrl": "/government/dashboard"
            }
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}", {}
    
    # ===================
    # VERIFICATION SERVICES
    # ===================
    
    async def send_phone_otp(self, phone: str, otp: str) -> bool:
        """Send OTP via SMS (Twilio integration)"""
        try:
            # TODO: Implement Twilio SMS sending
            # For now, just log the OTP (development mode)
            print(f"ðŸ“± SMS OTP for {phone}: {otp}")
            
            # Store OTP in cache/database with expiry
            # For simplicity, we'll use a simple in-memory store
            # In production, use Redis or database with TTL
            
            return True
        except Exception as e:
            print(f"âŒ Failed to send SMS OTP: {e}")
            return False
    
    async def verify_phone_otp(self, phone: str, otp: str) -> Tuple[bool, str]:
        """Verify phone OTP"""
        try:
            # TODO: Implement actual OTP verification
            # For development, accept any 6-digit OTP
            if len(otp) == 6 and otp.isdigit():
                # Update user phone verification status
                result = await self.users_collection.update_one(
                    {"phone": phone},
                    {
                        "$set": {
                            "phoneVerified": True,
                            "isVerified": True,
                            "updatedAt": datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    return True, "Phone verified successfully"
                else:
                    return False, "User not found"
            else:
                return False, "Invalid OTP format"
                
        except Exception as e:
            return False, f"OTP verification failed: {str(e)}"
    
    # ===================
    # LOGIN SERVICES
    # ===================
    
    async def authenticate_user(self, email: str, password: str, role: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Authenticate user login"""
        try:
            # Find user by email and role
            user = await self.users_collection.find_one({
                "email": email,
                "role": role
            })
            
            if not user:
                return False, "User not found", None
            
            # Verify password
            if not self.verify_password(password, user["passwordHash"]):
                return False, "Invalid password", None
            
            # Check if user is active
            if not user.get("isActive", False):
                return False, "Account is deactivated", None
            
            # For government users, check approval status
            if role == "government":
                gov_profile = user.get("governmentProfile", {})
                if gov_profile.get("approvalStatus") != "approved":
                    return False, "Account pending approval", None
            
            # Update last login
            await self.users_collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "lastLogin": datetime.utcnow(),
                        "loginAttempts": 0
                    }
                }
            )
            
            # Prepare user data for token
            user_data = {
                "userId": str(user["_id"]),
                "email": user["email"],
                "role": user["role"],
                "fullName": user["fullName"],
                "isVerified": user.get("isVerified", False)
            }
            
            return True, "Login successful", user_data
            
        except Exception as e:
            return False, f"Authentication failed: {str(e)}", None
    
    # ===================
    # WORKER TYPE SERVICES
    # ===================
    
    async def get_worker_types(self) -> List[Dict[str, Any]]:
        """Get all active worker types"""
        try:
            worker_types = []
            async for worker_type in self.worker_types_collection.find({"isActive": True}).sort("displayOrder", 1):
                worker_types.append({
                    "category": worker_type["category"],
                    "typeId": worker_type["typeId"],
                    "displayName": worker_type["displayName"],
                    "description": worker_type["description"],
                    "averageEarning": worker_type["averageEarning"],
                    "badge": worker_type["badge"],
                    "priority": worker_type["priority"],
                    "availableSpecializations": worker_type.get("availableSpecializations", [])
                })
            return worker_types
        except Exception as e:
            print(f"âŒ Error fetching worker types: {e}")
            return []
    
    async def get_form_configuration(self, role: str, worker_type: str = None) -> Dict[str, Any]:
        """Get dynamic form configuration based on role and worker type"""
        try:
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
                                "options": ["Yanamalakuduru", "Vijayawada", "Guntur"],
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
                        ],
                        "preferences": [
                            {
                                "field": "languagePreference",
                                "label": "Preferred Language",
                                "type": "select",
                                "options": ["en", "hi", "te", "ta"],
                                "required": True
                            },
                            {
                                "field": "notificationPreferences",
                                "label": "Notification Preferences",
                                "type": "multiselect",
                                "options": ["push", "sms", "email"],
                                "required": True
                            }
                        ]
                    },
                    "formSections": [
                        {"title": "Personal Information", "fields": "personal", "icon": "ðŸ‘¤"},
                        {"title": "Location Details", "fields": "location", "icon": "ðŸ“"},
                        {"title": "Preferences", "fields": "preferences", "icon": "âš™ï¸"}
                    ]
                }
            
            elif role == "worker" and worker_type:
                # Get worker type configuration from database
                worker_config = await self.worker_types_collection.find_one({
                    "typeId": worker_type,
                    "isActive": True
                })
                
                if worker_config:
                    return {
                        "role": "worker",
                        "workerType": worker_type,
                        "formFields": worker_config.get("formFields", {}),
                        "formSections": worker_config.get("formSections", []),
                        "requiredFields": worker_config.get("requiredFields", []),
                        "availableSpecializations": worker_config.get("availableSpecializations", [])
                    }
                else:
                    return {"error": "Worker type not found"}
            
            elif role == "government":
                return {
                    "role": "government",
                    "formFields": {
                        "personal": [
                            {
                                "field": "fullName",
                                "label": "Full Name",
                                "type": "text",
                                "placeholder": "Dr. Priya Sharma, IAS",
                                "required": True
                            },
                            {
                                "field": "officialEmail",
                                "label": "Official Email",
                                "type": "email",
                                "placeholder": "priya.sharma@ap.gov.in",
                                "required": True
                            },
                            {
                                "field": "personalEmail",
                                "label": "Personal Email (Optional)",
                                "type": "email",
                                "placeholder": "priya@gmail.com",
                                "required": False
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
                        "official": [
                            {
                                "field": "designation",
                                "label": "Designation",
                                "type": "text",
                                "placeholder": "Municipal Commissioner",
                                "required": True
                            },
                            {
                                "field": "department",
                                "label": "Department",
                                "type": "select",
                                "options": ["Urban Development", "Sanitation", "Public Works", "Environmental"],
                                "required": True
                            },
                            {
                                "field": "employeeCode",
                                "label": "Employee Code",
                                "type": "text",
                                "placeholder": "IAS-AP-2018-042",
                                "required": False
                            },
                            {
                                "field": "officeLevel",
                                "label": "Office Level",
                                "type": "select",
                                "options": ["state", "district", "municipal", "zone"],
                                "required": True
                            },
                            {
                                "field": "jurisdiction",
                                "label": "Jurisdiction",
                                "type": "text",
                                "placeholder": "Yanamalakuduru Municipal Corporation",
                                "required": True
                            },
                            {
                                "field": "currentPosting",
                                "label": "Current Posting",
                                "type": "text",
                                "placeholder": "Yanamalakuduru",
                                "required": True
                            }
                        ],
                        "office": [
                            {
                                "field": "officeAddress",
                                "label": "Office Address",
                                "type": "textarea",
                                "placeholder": "Collectorate, Yanamalakuduru, AP - 521456",
                                "required": True
                            },
                            {
                                "field": "officeContact",
                                "label": "Office Contact",
                                "type": "phone",
                                "placeholder": "+91-8765432100",
                                "required": False
                            },
                            {
                                "field": "secretaryName",
                                "label": "Secretary Name",
                                "type": "text",
                                "placeholder": "K. Rajesh",
                                "required": False
                            },
                            {
                                "field": "secretaryContact",
                                "label": "Secretary Contact",
                                "type": "phone",
                                "placeholder": "+91-9876543214",
                                "required": False
                            }
                        ]
                    },
                    "formSections": [
                        {"title": "Personal Information", "fields": "personal", "icon": "ðŸ‘¤"},
                        {"title": "Official Details", "fields": "official", "icon": "ðŸ›ï¸"},
                        {"title": "Office Information", "fields": "office", "icon": "ðŸ¢"}
                    ]
                }
            
            else:
                return {"error": "Invalid role or missing worker type"}
                
        except Exception as e:
            print(f"âŒ Error getting form configuration: {e}")
            return {"error": str(e)}

# ===================
# UTILITY FUNCTIONS
# ===================

async def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token"""
    auth_service = AuthService()
    payload = auth_service.verify_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("userId")
    if not user_id:
        return None
    
    try:
        from bson import ObjectId
        user = await auth_service.users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
            return user
        return None
    except Exception:
        return None

async def get_current_user(token: str):
    """Get current user from JWT token"""
    # This will be implemented later
    return None

async def create_default_worker_types():
    """Create default worker types in database"""
    auth_service = AuthService()
    
    default_worker_types = [
        {
            "category": "government_employee",
            "typeId": "municipal_cleaner",
            "displayName": "Municipal Cleaner",
            "description": "Government employed waste management specialist with official credentials",
            "formFields": {
                "professional": [
                    {
                        "field": "employeeId",
                        "label": "Employee ID",
                        "type": "text",
                        "placeholder": "MUN-2024-001",
                        "required": True
                    },
                    {
                        "field": "department",
                        "label": "Department",
                        "type": "select",
                        "options": ["Sanitation Department", "Public Works", "Environmental Services"],
                        "required": True
                    },
                    {
                        "field": "designation",
                        "label": "Designation",
                        "type": "text",
                        "placeholder": "Senior Cleaner",
                        "required": True
                    },
                    {
                        "field": "supervisorName",
                        "label": "Supervisor Name",
                        "type": "text",
                        "placeholder": "K. Venkata Rao",
                        "required": True
                    },
                    {
                        "field": "supervisorContact",
                        "label": "Supervisor Contact",
                        "type": "phone",
                        "placeholder": "+91-9876543211",
                        "required": True
                    },
                    {
                        "field": "workingArea",
                        "label": "Working Area",
                        "type": "text",
                        "placeholder": "Zone-3, Yanamalakuduru",
                        "required": True
                    },
                    {
                        "field": "specializations",
                        "label": "Specializations",
                        "type": "multiselect",
                        "options": ["general_waste", "bulk_collection", "street_cleaning", "drain_cleaning"],
                        "required": True
                    },
                    {
                        "field": "workExperience",
                        "label": "Work Experience (Years)",
                        "type": "number",
                        "min": 0,
                        "max": 50,
                        "required": True
                    }
                ],
                "banking": [
                    {
                        "field": "bankAccountNumber",
                        "label": "Bank Account Number",
                        "type": "text",
                        "placeholder": "12345678901234",
                        "required": True
                    },
                    {
                        "field": "ifscCode",
                        "label": "IFSC Code",
                        "type": "text",
                        "placeholder": "SBIN0001234",
                        "required": True
                    },
                    {
                        "field": "accountHolderName",
                        "label": "Account Holder Name",
                        "type": "text",
                        "placeholder": "Same as registered name",
                        "required": True
                    }
                ]
            },
            "formSections": [
                {"title": "Professional Details", "fields": "professional", "icon": "ðŸ›ï¸"},
                {"title": "Banking Information", "fields": "banking", "icon": "ðŸ’³"}
            ],
            "requiredFields": ["employeeId", "department", "designation", "supervisorName", "specializations"],
            "availableSpecializations": ["general_waste", "bulk_collection", "street_cleaning", "drain_cleaning", "park_maintenance"],
            "averageEarning": "â‚¹150-400 per job",
            "badge": "ðŸ›ï¸ Municipal Specialist",
            "priority": "high",
            "trustLevel": "verified",
            "isActive": True,
            "displayOrder": 1,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "category": "ngo_worker",
            "typeId": "ngo_plastic_specialist",
            "displayName": "NGO - Plastic Waste Specialist",
            "description": "NGO affiliated worker specializing in plastic waste collection and recycling",
            "formFields": {
                "ngo": [
                    {
                        "field": "ngoName",
                        "label": "NGO Name",
                        "type": "text",
                        "placeholder": "Green Earth Foundation",
                        "required": True
                    },
                    {
                        "field": "ngoRegistrationNumber",
                        "label": "NGO Registration Number",
                        "type": "text",
                        "placeholder": "NGO-AP-2020-001",
                        "required": True
                    },
                    {
                        "field": "roleInNGO",
                        "label": "Role in NGO",
                        "type": "select",
                        "options": ["Volunteer", "Coordinator", "Manager", "Field Worker"],
                        "required": True
                    },
                    {
                        "field": "specializations",
                        "label": "Plastic Specializations",
                        "type": "multiselect",
                        "options": ["plastic_bottles", "plastic_bags", "packaging_waste", "microplastics"],
                        "required": True
                    },
                    {
                        "field": "workExperience",
                        "label": "Experience (Years)",
                        "type": "number",
                        "min": 0,
                        "max": 20,
                        "required": True
                    }
                ],
                "banking": [
                    {
                        "field": "bankAccountNumber",
                        "label": "Bank Account Number",
                        "type": "text",
                        "placeholder": "12345678901235",
                        "required": True
                    },
                    {
                        "field": "ifscCode",
                        "label": "IFSC Code",
                        "type": "text",
                        "placeholder": "SBIN0001234",
                        "required": True
                    },
                    {
                        "field": "accountHolderName",
                        "label": "Account Holder Name",
                        "type": "text",
                        "placeholder": "Same as registered name",
                        "required": True
                    }
                ]
            },
            "formSections": [
                {"title": "NGO Details", "fields": "ngo", "icon": "ðŸ¤"},
                {"title": "Banking Information", "fields": "banking", "icon": "ðŸ’³"}
            ],
            "requiredFields": ["ngoName", "roleInNGO", "specializations"],
            "availableSpecializations": ["plastic_bottles", "plastic_bags", "packaging_waste", "microplastics", "plastic_furniture"],
            "averageEarning": "â‚¹300-800 per job",
            "badge": "ðŸ¤ Community Champion",
            "priority": "medium",
            "trustLevel": "community",
            "isActive": True,
            "displayOrder": 2,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        },
        {
            "category": "independent_worker",
            "typeId": "general_cleaner",
            "displayName": "Independent General Cleaner",
            "description": "Skilled independent worker providing flexible waste management services",
            "formFields": {
                "experience": [
                    {
                        "field": "workExperience",
                        "label": "Work Experience",
                        "type": "select",
                        "options": ["0-1 years", "1-3 years", "3-5 years", "5+ years"],
                        "required": True
                    },
                    {
                        "field": "skillAreas",
                        "label": "Skill Areas",
                        "type": "multiselect",
                        "options": ["house_cleaning", "garden_waste", "general_sorting", "small_repairs"],
                        "required": True
                    },
                    {
                        "field": "ownEquipment",
                        "label": "Own Equipment",
                        "type": "multiselect",
                        "options": ["cleaning_tools", "bicycle", "motorcycle", "protective_gear"],
                        "required": False
                    },
                    {
                        "field": "transportationMode",
                        "label": "Transportation",
                        "type": "select",
                        "options": ["walking", "bicycle", "motorcycle", "auto", "public_transport"],
                        "required": True
                    }
                ],
                "banking": [
                    {
                        "field": "bankAccountNumber",
                        "label": "Bank Account Number",
                        "type": "text",
                        "placeholder": "12345678901236",
                        "required": True
                    },
                    {
                        "field": "ifscCode",
                        "label": "IFSC Code",
                        "type": "text",
                        "placeholder": "SBIN0001234",
                        "required": True
                    },
                    {
                        "field": "accountHolderName",
                        "label": "Account Holder Name",
                        "type": "text",
                        "placeholder": "Same as registered name",
                        "required": True
                    }
                ]
            },
            "formSections": [
                {"title": "Experience & Skills", "fields": "experience", "icon": "ðŸ’¼"},
                {"title": "Banking Information", "fields": "banking", "icon": "ðŸ’³"}
            ],
            "requiredFields": ["workExperience", "skillAreas", "transportationMode"],
            "availableSpecializations": ["house_cleaning", "garden_waste", "general_sorting", "small_repairs", "apartment_cleaning"],
            "averageEarning": "â‚¹200-500 per job",
            "badge": "ðŸ’¼ Eco Entrepreneur",
            "priority": "medium",
            "trustLevel": "basic",
            "isActive": True,
            "displayOrder": 3,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
    ]
    
    # Insert worker types if they don't exist
    for worker_type_data in default_worker_types:
        existing = await auth_service.worker_types_collection.find_one({
            "category": worker_type_data["category"],
            "typeId": worker_type_data["typeId"]
        })
        
        if not existing:
            await auth_service.worker_types_collection.insert_one(worker_type_data)
            print(f"âœ… Created worker type: {worker_type_data['displayName']}")

# Global auth service instance
auth_service = AuthService()